#!/usr/bin/env python3
"""Small EV-export regression harness; not a full solver integration test."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class EvExportRegression(unittest.TestCase):
    def test_compiled_normalization_and_actual_setter(self):
        source = (ROOT / "src/trainable/DiscountedCfrTrainable.cpp").read_text()
        setter = source[source.index("void DiscountedCfrTrainable::setEv("):source.index("json DiscountedCfrTrainable::dump_evs()")]
        harness = r"""
#include "solver/EvExport.h"
#include <cassert>
#include <vector>
#include <limits>
#include <iostream>
using namespace std;
struct DiscountedCfrTrainable {
    vector<float> evs;
    int action_number=2, card_number=2;
    void setEv(const vector<float>&);
};
""" + setter + r"""
int main() {
    assert(ev_export::normalize(6, 2)==3);
    assert(ev_export::normalize(-6, 2)==-3);
    assert(ev_export::normalize(0, 0)==0);
    // Separate rank buckets can retain a tiny compatible utility even when
    // total reach loses it next to a blocking mass in single precision.
    volatile float blocked=1.0f, compatible=1e-8f;
    float total=blocked+compatible;
    float denominator=total-blocked;
    assert(denominator==0);
    float utility=compatible;
    assert(isinf(utility/denominator));
    assert(ev_export::normalize(utility, denominator)==0);
    for (float bad : {numeric_limits<float>::infinity(),
                      -numeric_limits<float>::infinity(),
                      numeric_limits<float>::quiet_NaN()}) {
        bool threw=false;
        try { ev_export::normalize(bad,1); } catch(const runtime_error&) { threw=true; }
        assert(threw);
    }
    bool overflow=false;
    try { ev_export::normalize(numeric_limits<float>::max(),
                              numeric_limits<float>::min()); }
    catch(const runtime_error&) { overflow=true; }
    assert(overflow);
    DiscountedCfrTrainable t;
    t.setEv({1,2,3,4});
    assert(t.evs==vector<float>({1,2,3,4}));
    t.setEv({numeric_limits<float>::quiet_NaN(),2,3,4});
    assert(t.evs[0]==1); // preserve legacy NaN-skip convention
    for (float bad : {numeric_limits<float>::infinity(), -numeric_limits<float>::infinity()}) {
        bool threw=false;
        try { t.setEv({bad,2,3,4}); } catch(const runtime_error&) { threw=true; }
        assert(threw);
    }
    bool mismatch=false;
    try { t.setEv({1}); } catch(const runtime_error&) { mismatch=true; }
    assert(mismatch);
    cout << "normalization + actual setEv regression: PASS\n";
}
"""
        with tempfile.TemporaryDirectory() as d:
            src=pathlib.Path(d)/"regression.cpp"; exe=pathlib.Path(d)/"regression"
            src.write_text(harness)
            subprocess.run(["g++","-std=c++11","-Wall","-Wextra","-I",str(ROOT/"include"),str(src),"-o",str(exe)],check=True)
            subprocess.run([str(exe)],check=True)

    def test_collection_bypasses_all_warmup_chance_branches(self):
        s=(ROOT/"src/solver/PCfrSolver.cpp").read_text()
        self.assertIn("if(iter <= this->warmup && !this->collecting_statics){",s)
        self.assertIn("if (iter <= this->warmup && !this->collecting_statics && multiplier[card] == 0) continue;",s)
        self.assertIn("if(iter > this->warmup || this->collecting_statics) {",s)
        # Coverage regression for the exact boundary conditions. No RNG/solver run.
        for iteration in (0,5,10,11):
            for collecting in (False,True):
                sampled=iteration<=10 and not collecting
                selected=[i for i,m in enumerate((4,0,0,0)) if not(sampled and m==0)]
                self.assertEqual(len(selected),1 if sampled else 4)
        self.assertIn("ev_export::normalize((all_action_utility[action_id])[hand_id], rp_sum)",s)
        self.assertIn("!this->distributing_task && !this->collecting_statics",s)

if __name__=="__main__": unittest.main(verbosity=2)

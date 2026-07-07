#!/usr/bin/env python
"""Dump the covariance matrices out of the TCanvas-wrapped ROOT files.
Run with ROOT available:  python extract_cov.py   (or `root -l -b -q extract_cov.py`)
Writes cov_numubar.csv and cov_numu_numubar.csv next to the inputs."""
import ROOT

for fn, name in [("Covariance_Matrix_Numubar.root", "numubar"),
                 ("Covariance_Matrix_Numu+Numubar.root", "numu_numubar")]:
    f = ROOT.TFile(fn)
    c = f.Get("c1")
    th2 = next((o for o in c.GetListOfPrimitives() if o.InheritsFrom("TH2")), None)
    if not th2:
        print(fn, "-> no TH2 found"); continue
    nx, ny = th2.GetNbinsX(), th2.GetNbinsY()
    labels = [th2.GetXaxis().GetBinLabel(i) or f"bin{i}" for i in range(1, nx + 1)]
    with open(f"cov_{name}.csv", "w") as out:
        out.write("# labels: " + " | ".join(labels) + "\n")
        for i in range(1, nx + 1):
            out.write(",".join(f"{th2.GetBinContent(i, j):.6e}" for j in range(1, ny + 1)) + "\n")
    print(f"{name}: {nx}x{ny} written to cov_{name}.csv  (labels: {labels})")

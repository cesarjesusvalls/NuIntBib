// Dump the covariance TH2 out of the TCanvas-wrapped ROOT files.
// Run:  root -l -b -q extract_cov.C
void extract_cov() {
  const char* files[] = {"Covariance_Matrix_Numubar.root", "Covariance_Matrix_Numu+Numubar.root"};
  const char* names[] = {"numubar", "numu_numubar"};
  for (int k = 0; k < 2; ++k) {
    TFile* f = TFile::Open(files[k]);
    TCanvas* c = (TCanvas*) f->Get("c1");
    TH2* h = nullptr;
    TIter next(c->GetListOfPrimitives());
    TObject* o;
    while ((o = next())) if (o->InheritsFrom("TH2")) { h = (TH2*)o; break; }
    if (!h) { printf("%s: no TH2 found\n", names[k]); continue; }
    int nx = h->GetNbinsX(), ny = h->GetNbinsY();
    TString labs;
    for (int i = 1; i <= nx; ++i) { if (i>1) labs += " | "; labs += h->GetXaxis()->GetBinLabel(i); }
    FILE* out = fopen(Form("cov_%s.csv", names[k]), "w");
    fprintf(out, "# %d x %d covariance; x/y bins: %s\n", nx, ny, labs.Data());
    for (int i = 1; i <= nx; ++i) {
      for (int j = 1; j <= ny; ++j) fprintf(out, "%s%.6e", j>1?",":"", h->GetBinContent(i,j));
      fprintf(out, "\n");
    }
    fclose(out);
    printf("%s: %dx%d written (bins: %s)\n", names[k], nx, ny, labs.Data());
    f->Close();
  }
}

Data release for the NC1pi+ cross-section measurement by the T2K experiment reported in:
arXiv:2503.06849 and arXiv:2503.06843

- result_with_bins.txt contains the double differential cross section result including bin information.

- covariance_matrix.txt contains the values of the covariance matrix with the bins in the same order as result_with_bins.txt. The covariance does not include any normalization. To use it with the results one needs to undo the normalization applied to the result and the error by multiplying the result by its 2D area (Delta costheta x Delta momentum). To be explicit:
Sqrt(cov[i,i]) matches the Error in result_with_bins.txt after the error is multiplied by Delta costheta * Delta momentum. For instance, for the 0-th bin:

cov[0,0] = 3.244408e-83
sqrt(cov[0,0]) = 5.695971e-42
data_err[0] = 0.7120e-40
delta_momentum[0] = 0.6-0.2 = 0.4
delta_costheta[0] = 0.7-0.5 = 0.2
data_err * delta_costheta * delta_momentum = 5.695971e-42

-flux_release.root contains the postfit T2K flux for all flavors: muon neutrino (numu), muon antineutrino (numub), electron neutrino (nue), electron antineutrino (nueb).
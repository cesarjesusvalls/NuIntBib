$(TARGET).pdf: FORCE
	pdflatex $(TARGET)
	bibtex $(TARGET)
	pdflatex $(TARGET)
	pdflatex $(TARGET)

# $(TARGET).ps: $(TARGET).dvi
# 	dvips $(TARGET)

# $(TARGET).ps.gz: $(TARGET).ps
# 	gzip -f $(TARGET).ps

# $(TARGET).pdf: $(TARGET).dvi
# 	dvipdf $(TARGET)

# $(TARGET).dvi: $(TARGET).tex  FORCE
# 	latex $(TARGET)
# 	latex $(TARGET)
# 	latex $(TARGET)

zip: veryclean
	/bin/rm -f $(TARGET).zip
	zip -r $(TARGET).zip . -x $(TARGET).zip

arxiv: veryclean
	/bin/rm -f $(TARGET)-arxiv.zip
	pdflatex $(TARGET)
	bibtex $(TARGET)
	zip -r $(TARGET)-arxiv.zip *.tex *.bib latex-doc.mk Makefile $(TARGET).bbl figures/*.pdf -x supplement*.tex -x $(TARGET)-arxiv.zip

clean: FORCE
	/bin/rm -f *.aux $(TARGET).log $(TARGET).dvi $(TARGET).toc $(TARGET).lot $(TARGET).lof $(TARGET).ps $(TARGET).ps.gz $(TARGET).pdf $(TARGET)Notes.bib $(TARGET).blg $(TARGET).bbl $(TARGET).out

veryclean: clean
	/bin/rm -f *~

compress: FORCE clean
	gzip *ps

uncompress: FORCE
	gunzip *.gz

FORCE:

.phony: FORCE clean



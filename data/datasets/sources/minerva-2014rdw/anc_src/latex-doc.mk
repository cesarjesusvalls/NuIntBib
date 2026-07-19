$(TARGET).pdf: FORCE
	-pdflatex -interaction=nonstopmode -shell-escape $(TARGET)
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
	-pdflatex -interaction=nonstopmode -shell-escape $(TARGET)
	bibtex $(TARGET)
	pdflatex $(TARGET)
	pdflatex $(TARGET)
	zip -r $(TARGET)-arxiv.zip *.tex latex-doc.mk Makefile $(TARGET).bbl figures/*.pdf -x supplement*.tex -x $(TARGET)-arxiv.zip -x PRL-$(TARGET).tex supplement-NukeCC.tex
	###########################################
	#Submit only $(TARGET)-arxiv.zip
	###########################################



prl: veryclean
	-rm -rf PRL-submission
	./mergeLatex.sh $(TARGET).tex PRL-$(TARGET).tex
	#make the whole thing to get pdfs, bbl and merged tex
	-pdflatex -interaction=nonstopmode -shell-escape PRL-$(TARGET)
	bibtex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)
	#put it all into one directory
	-mkdir PRL-submission
	cp PRL-$(TARGET).tex PRL-submission
	cp PRL-$(TARGET).bbl PRL-submission
	cp figures/*.pdf PRL-submission
	cp $(TARGET).bib PRL-submission
	#edit the figure location to be here instead of a figures directory
	perl -wpi -e 's[\\graphicspath.*][]' PRL-submission/PRL-$(TARGET).tex
	tar -cf PRL-submission/main-files.tar PRL-submission/*
	#now make the supplemental material
	./mergeLatex.sh supplement-NukeCC.tex PRL-supplement-NukeCC.tex
	pdflatex PRL-supplement-NukeCC
	bibtex PRL-supplement-NukeCC
	pdflatex PRL-supplement-NukeCC
	pdflatex PRL-supplement-NukeCC
	cp PRL-supplement-NukeCC.tex PRL-submission
	cp PRL-supplement-NukeCC.bbl PRL-submission
	###########################################
	#Submit PRL-submission/main-files.tar as the main file 
	#Submit PRL-submission/PRL-supplement-NukeCC.tex
	#   and PRL-submission/PRL-supplement-NukeCC.bbl as supplemental files
	###########################################
	

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



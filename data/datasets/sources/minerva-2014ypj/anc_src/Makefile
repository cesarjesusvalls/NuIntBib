TARGET = ProtonCCQElike

default: $(TARGET).pdf supplement-ProtonCCQElike.pdf PRL-$(TARGET).pdf

supplement-ProtonCCQElike.pdf: supplement-ProtonCCQElike.tex
	pdflatex supplement-ProtonCCQElike

PRL-$(TARGET).pdf: PRL-$(TARGET).tex
	pdflatex PRL-$(TARGET)
	bibtex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)

PRL-$(TARGET).tex: FORCE
	./mergeLatex.sh $(TARGET).tex PRL-$(TARGET).tex


suppclean: FORCE
	/bin/rm -f *.aux supplement-ProtonCCQElike.log supplement-ProtonCCQElike.dvi supplement-ProtonCCQElike.toc supplement-ProtonCCQElike.lot supplement-ProtonCCQElike.lof supplement-ProtonCCQElike.ps supplement-ProtonCCQElike.ps.gz supplement-ProtonCCQElike.pdf supplement-ProtonCCQElike.bib supplement-ProtonCCQElike.blg supplement-ProtonCCQElike.bbl supplement-ProtonCCQElike.out

prlclean: FORCE
	/bin/rm -f *.aux PRL-$(TARGET).tex PRL-$(TARGET).log PRL-$(TARGET).dvi PRL-$(TARGET).toc PRL-$(TARGET).lot PRL-$(TARGET).lof PRL-$(TARGET).ps PRL-$(TARGET).ps.gz PRL-$(TARGET).pdf PRL-$(TARGET)Notes.bib PRL-$(TARGET).blg PRL-$(TARGET).bbl PRL-$(TARGET).out

allclean: prlclean suppclean clean

include latex-doc.mk


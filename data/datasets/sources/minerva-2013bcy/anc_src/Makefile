TARGET = CCQE-nubar

default: $(TARGET).pdf supplement-nubar.pdf PRL-$(TARGET).pdf

supplement-nubar.pdf: supplement-nubar.tex
	pdflatex supplement-nubar

PRL-$(TARGET).pdf: PRL-$(TARGET).tex
	pdflatex PRL-$(TARGET)
	bibtex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)

PRL-$(TARGET).tex: FORCE
	./mergeLatex.sh $(TARGET).tex PRL-$(TARGET).tex


suppclean: FORCE
	/bin/rm -f *.aux supplement-nubar.log supplement-nubar.dvi supplement-nubar.toc supplement-nubar.lot supplement-nubar.lof supplement-nubar.ps supplement-nubar.ps.gz supplement-nubar.pdf supplement-nubarNotes.bib supplement-nubar.blg supplement-nubar.bbl supplement-nubar.out

prlclean: FORCE
	/bin/rm -f *.aux PRL-$(TARGET).tex PRL-$(TARGET).log PRL-$(TARGET).dvi PRL-$(TARGET).toc PRL-$(TARGET).lot PRL-$(TARGET).lof PRL-$(TARGET).ps PRL-$(TARGET).ps.gz PRL-$(TARGET).pdf PRL-$(TARGET)Notes.bib PRL-$(TARGET).blg PRL-$(TARGET).bbl PRL-$(TARGET).out

allclean: prlclean suppclean clean

include latex-doc.mk


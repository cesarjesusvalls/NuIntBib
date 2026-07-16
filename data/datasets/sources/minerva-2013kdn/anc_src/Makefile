TARGET = CCQE-nu

default: $(TARGET).pdf supplement-nu.pdf PRL-$(TARGET).pdf

supplement-nu.pdf: supplement-nu.tex
	pdflatex supplement-nu

PRL-$(TARGET).pdf: PRL-$(TARGET).tex
	pdflatex PRL-$(TARGET)
	bibtex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)
	pdflatex PRL-$(TARGET)

PRL-$(TARGET).tex: FORCE
	./mergeLatex.sh $(TARGET).tex PRL-$(TARGET).tex


suppclean: FORCE
	/bin/rm -f *.aux supplement-nu.log supplement-nu.dvi supplement-nu.toc supplement-nu.lot supplement-nu.lof supplement-nu.ps supplement-nu.ps.gz supplement-nu.pdf supplement-nuNotes.bib supplement-nu.blg supplement-nu.bbl supplement-nu.out

prlclean: FORCE
	/bin/rm -f *.aux PRL-$(TARGET).tex PRL-$(TARGET).log PRL-$(TARGET).dvi PRL-$(TARGET).toc PRL-$(TARGET).lot PRL-$(TARGET).lof PRL-$(TARGET).ps PRL-$(TARGET).ps.gz PRL-$(TARGET).pdf PRL-$(TARGET)Notes.bib PRL-$(TARGET).blg PRL-$(TARGET).bbl PRL-$(TARGET).out

allclean: prlclean suppclean clean


include latex-doc.mk


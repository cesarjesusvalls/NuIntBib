
TARGET = CCInclNukeTarget

default: $(TARGET).pdf PRL-supplement-NukeCC.pdf PRL-$(TARGET).pdf
#default: $(TARGET).pdf PRL-$(TARGET).pdf

supplement-NukeCC.pdf: supplement-NukeCC.tex
	pdflatex supplement-NukeCC
	bibtex supplement-NukeCC
	pdflatex supplement-NukeCC
	pdflatex supplement-NukeCC

PRL-$(TARGET).pdf: PRL-$(TARGET).tex
	pdflatex -shell-escape PRL-$(TARGET)
	bibtex PRL-$(TARGET)
	pdflatex -shell-escape PRL-$(TARGET)
	pdflatex PRL-$(TARGET)

PRL-$(TARGET).tex: FORCE
	./mergeLatex.sh $(TARGET).tex PRL-$(TARGET).tex

PRL-supplement-NukeCC.pdf: FORCE
	./mergeLatex.sh supplement-NukeCC.tex PRL-supplement-NukeCC.tex
	pdflatex PRL-supplement-NukeCC
	bibtex PRL-supplement-NukeCC
	pdflatex PRL-supplement-NukeCC
	pdflatex PRL-supplement-NukeCC

suppclean: FORCE
	/bin/rm -f *.aux supplement-NukeCC.log supplement-NukeCC.dvi supplement-NukeCC.toc supplement-NukeCC.lot supplement-NukeCC.lof supplement-NukeCC.ps supplement-NukeCC.ps.gz supplement-NukeCC.pdf supplement-nuNotes.bib supplement-NukeCC.blg supplement-NukeCC.bbl supplement-NukeCC.out

prlclean: FORCE
	/bin/rm -f *.aux PRL-$(TARGET).tex PRL-$(TARGET).log PRL-$(TARGET).dvi PRL-$(TARGET).toc PRL-$(TARGET).lot PRL-$(TARGET).lof PRL-$(TARGET).ps PRL-$(TARGET).ps.gz PRL-$(TARGET).pdf PRL-$(TARGET)Notes.bib PRL-$(TARGET).blg PRL-$(TARGET).bbl PRL-$(TARGET).out

allclean: prlclean suppclean clean

include latex-doc.mk


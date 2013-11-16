NAME = model

LATEX       = pdflatex
CHECK_RERUN = grep Rerun $*.log
TMP_SUFFS   = pdf aux bbl blg log dvi ps eps

.SUFFIXES: .tex .dvi .ps .pdf

default: ${NAME}.pdf

%.pdf: %.tex
	${LATEX} $<
	( ${CHECK_RERUN} && ${LATEX} $< ) || echo "All done."
	( ${CHECK_RERUN} && ${LATEX} $< ) || echo "All done."

clean:
	rm -rf $(foreach suff, ${TMP_SUFFS}, ${NAME}.${suff})

#! /bin/sh

tmpFile=./tmp-mergeLatex

if [ $# -eq 2 ]
  then
# have to run this script twice because of nested \input commands
# first pass
    awk '!/input\{/ {print}
/input\{/ {
sub (/input\{/,"")
sub (/\}.*/,"")
cmd= "cat ./"$1""
system(cmd)
}' $1 > $tmpFile
# second pass
    awk '!/input\{/ {print}
/input\{/ {
sub (/input\{/,"")
sub (/\}.*/,"")
cmd= "cat ./"$1""
system(cmd)
}' $tmpFile > $2
    /bin/rm $tmpFile
  else
    echo "Usage: mergeLatex.sh input-filename output-filename"
    echo "  include '.tex' suffix in filenames"
fi



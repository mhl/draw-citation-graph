#!/usr/bin/python2.5

# This is an attempt to build a (most likely incomplete) citation
# graph from a BibTeX file and a directory of PDFs whose names
# correspond to your BibTeX keys, e.g. if you have an entry:
#
# @article{ Hanesch1989,
#   author = {Hanesch, U. and K.-F. Fischbach and M. Heisenberg},
#   title = {Neuronal architecture of the central complex in Drosophila melanogaster},
#   year = {1989},
#   journal = {Cell Tissue Research},
#   volume = {257},
#   pages = {343-366}
# }
#
# ... then the file should be called Hanesch1989.pdf
#
# This will produce a graph in Graphviz's dot format on standard
# output.  If you supply a TeX file as the last parameter, it will
# attempt to start include every citation in that file in the graph.
# If you don't, it will attempt to include every work in the .bib
# file.
#
# To generate a PNG citation graph, you could do something like:
#
#   draw-citation-graph references.bib papers/ aargh2.tex > test.dot
#
# .. and then:
#
#   neato -Tpng -o test-neato.png < test.dot
#
# Depends on: apt-get install python-bibtex
#
# Copyright 2009 Mark Longair
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import _bibtex
import sets
import os
import re
import colorsys
from subprocess import check_call
from stat import ST_MTIME

def usage_and_exit(extra_message=None):
    if extra_message:
        print extra_message
    print "Usage: draw-citation-graph BIBTEX-FILE PDF-DIRECTORY [TEX-DOCUMENT]"
    sys.exit(1)

if not (len(sys.argv) == 3 or len(sys.argv) == 4):
    usage_and_exit()

pdf_directory = sys.argv[2]
bibtex_file = sys.argv[1]
tex_file = None
if len(sys.argv) == 4:
    tex_file = sys.argv[3]

if not os.path.exists(pdf_directory):
    usage_and_exit("The PDF directory '"+pdf_directory+"' doesn't exist.")

if not os.path.isdir(pdf_directory):
    usage_and_exit("'"+pdf_directory+"' is not a directory.")

if tex_file and not os.path.exists(tex_file):
    usage_and_exit("The TeX file '"+tex_file+"' does not exist.")

b = _bibtex.open_file(bibtex_file,1) # The second parameter means "strict"

class Paper:
    def __init__(self,key,title,year):
        self.key = key
        self.title = title
        self.year = year
    def __eq__(self,other):
        return self.key == other.key
    def __cmp__(self,other):
        return cmp(self.key,other.key)
    def __hash__(self):
        return self.key.__hash__()
    def pdf_filename(self):
        return os.path.join(pdf_directory,self.key+".pdf")
    def text_filename(self):
        return os.path.join(pdf_directory,self.key+".txt")
    # Try to make a text version of the paper, return a boolean
    # indicating if it succeeded:
    def update_text_file(self):
        t = self.text_filename()
        p = self.pdf_filename()
        if not os.path.exists(p):
            return False
        regenerate = False
        if not os.path.exists(t):
            regenerate = True
        if os.path.exists(t) and os.stat(t)[ST_MTIME] < os.stat(p)[ST_MTIME]:
            regenerate = True
        if regenerate:
            check_call( [ "pdftotext", p, t ] )
        return True
    def make_title_re(self):
        re_text = re.sub('\s+','\s+',self.title)
        return re.compile(re_text,re.IGNORECASE|re.MULTILINE)
    def contains_re(self,re_object):
        if self.update_text_file():
            fp = open(self.text_filename())
            paper_text = fp.read()
            fp.close()
            return re_object.search(paper_text)
        else:
            return False
    def year_as_int(self):
        m = re.search('^(\d+)',self.year)
        if m:
            return int(m.group(1))
        else:
            return None
    def __str__(self):
        return self.key+" ["+self.year+"] '"+self.title+"'"

bibtex_papers = set([])

start_keys = set([])

papers_with_pdf_versions = set([])

if tex_file:
    fp = open(tex_file,"r")
    matches = re.findall('\\cite.{([^}]+)}',fp.read())
    fp.close()
    for m in matches:
        for k in m.split(','):
            start_keys.add(k)

keys_to_papers = {}

while True:
    be = _bibtex.next(b)
    if not be:
        break
    key = be[0]
    print >> sys.stderr, "===" + str(key)
    bh = be[4]
    h = {}
    for k in be[4].keys ():
        h[k] = _bibtex.expand(b,bh[k],-1)
    if ("title" in h) and ("year" in h):
        t = h["title"]
        y = h["year"]
        p = Paper(key,t[2],y[2])
        bibtex_papers.add(p)
        keys_to_papers[key] = p
        paper_pdf_file = os.path.join(pdf_directory,key+".pdf")
        if os.path.exists(paper_pdf_file):
            papers_with_pdf_versions.add(p)
        else:
            print >> sys.stderr, "Warning: no PDF file "+paper_pdf_file
        if not tex_file:
            start_keys.add(key)

earliest_year = 10000
latest_year = 0

earliest_hue = 0.83
latest_hue = 0

def year_to_hsv(y):
    p = (y - earliest_year) / float(latest_year - earliest_year)
    h = p * (latest_hue - earliest_hue) + earliest_hue
    return (h,1,1)

print >> sys.stderr, "Start keys are: "
for k in start_keys:
    print >> sys.stderr, "  "+k
    if k in keys_to_papers:
        y = keys_to_papers[k].year_as_int()
        if y < earliest_year:
            earliest_year = y
        if y > latest_year:
            latest_year = y

print >> sys.stderr, "Earliest year is: "+str(earliest_year)
print >> sys.stderr, "Latest year is: "+str(latest_year)

print '''digraph citations {
    overlap=scale
    splines=true
    sep=0.1
    node [fontname="DejaVuSans"]
'''

nodes_with_connections = set([])
connections = []

for k in start_keys:
    print >> sys.stderr, "Starting with key "+k
    if not k in keys_to_papers:
        print >> sys.stderr, "Warning: no information for start key "+k
        continue
    start_paper = keys_to_papers[k]
    title_re_object = start_paper.make_title_re()
    # The stupidly O(n^2) bit:
    for p in papers_with_pdf_versions:
        if k == p.key:
            continue
        # print >> sys.stderr, "Looking for title '%s' in paper '%s':" % (str(title_re_object.pattern),str(p))
        if p.contains_re(title_re_object):
            nodes_with_connections.add(k)
            nodes_with_connections.add(p.key)
            connections.append("    \"%s\" -> \"%s\"" % (p.key,k))

for k in nodes_with_connections:
    if not k in keys_to_papers:
        print >> sys.stderr, "Warning: no information for start key "+k
        continue
    start_paper = keys_to_papers[k]
    hsv = year_to_hsv(start_paper.year_as_int())
    print "    \"%s\" [style=filled fillcolor=\"%f, %f, %f\"]" % (k,hsv[0],hsv[1],hsv[2])

for c in connections:
    print c

print "}"

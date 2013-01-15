from cStringIO import StringIO
import logging
from logging import Formatter, DEBUG, INFO
from logging.handlers import RotatingFileHandler
import os
import shlex
import shutil
import subprocess
import tempfile

from flask import Flask, request, render_template, make_response
app = Flask(__name__)

if not app.debug:
    # INFO logs
    handler = RotatingFileHandler("logs/info.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(INFO)
    app.logger.addHandler(handler)

    # DEBUG logs
    handler = RotatingFileHandler("logs/debug.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(DEBUG)
    app.logger.addHandler(handler)
    app.logger.setLevel(DEBUG)

languages = ['Python', 'Ruby', 'Java', 'C', 'C++', 'SQL', 'XML', 'HTML',
             'Haskell', 'Lisp', 'erlang', 'ABAP', 'ACSL', 'Ada', 'Algol',
             'Ant', 'Assembler', 'Awk', 'bash', 'Basic', 'Caml', 'CIL',
             'Clean', 'Cobol', 'Comal 80', 'command.com', 'Comsol',
             'csh', 'Delphi', 'Eiffel', 'Elan', 'Euphoria', 'Fortran',
             'GCL', 'Gnuplot', 'IDL', 'inform', 'JVMIS', 'ksh', 'Lingo',
             'Logo', 'make', 'Mathematica', 'Matlab', 'Mercury',
             'MetaPost', 'Miranda', 'Mizar', 'ML', 'Modula-2', 'MuPAD',
             'NASTRAN', 'Oberon-2', 'OCL', 'Octave', 'Oz', 'Pascal',
             'Perl', 'PHP', 'PL/I', 'Plasm', 'PostScript', 'POV',
             'Prolog', 'Promela', 'PSTricks', 'R', 'Reduce', 'Rexx',
             'RSL', 'S', 'SAS', 'Scilab', 'sh', 'SHELXL', 'Simula',
             'SPARQL', 'tcl', 'TeX', 'VBScript', 'Verilog', 'VHDL',
             'VRML', 'XSLT']

@app.route("/")
def index():
    return render_template("index.html", source=open("main.py").read(), languages=languages)

@app.route("/render", methods=["POST"])
def render():
    lang = request.form['lang']
    source = request.form['source']
    mode = request.form['mode']
    assert lang in languages

    wd = tempfile.mkdtemp()
    app.logger.info("Creating temp directory %s" % wd)

    latexBody = render_template("source-listing.tex", lang=lang, source=source)
    inFile = StringIO(latexBody)
    standalone = os.path.join(os.getcwd(), "standalone")
    env = os.environ
    env["TEXINPUTS"] = ".:%s:" % standalone
    p1 = subprocess.Popen(["pdflatex"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
           cwd=wd, shell=True, env=env)
    (stdout, stderr) = p1.communicate(latexBody)
    app.logger.debug("pdflatex stdout: %s" % stdout)
    app.logger.debug("pdflatex stderr: %s" % stderr)

    p2args = shlex.split("convert -density 300 texput.pdf -quality 90 texput.png")
    p2 = subprocess.Popen(p2args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
    (stdout, stderr) = p2.communicate()
    app.logger.debug("convert stdout: %s" % stdout)
    app.logger.debug("convert stderr: %s" % stderr)

    png = open(os.path.join(wd, "texput.png"), "r").read()
    resp = make_response(png)
    resp.headers["Content-Type"] = "image/png"

    if mode == "download":
        resp.headers["Content-Disposition"] = "attachment; filename=%s-listing.png" % lang.lower()

    app.logger.info("Removing %s" % wd)
    shutil.rmtree(wd)
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

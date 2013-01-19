from cStringIO import StringIO
from itertools import count
import logging
from logging import Formatter, DEBUG, INFO
from logging.handlers import RotatingFileHandler
import os
import shlex
import shutil
import subprocess
import tempfile
import time

from webcolors import hex_to_rgb
from flask import Flask, abort, request, render_template, make_response

import extras

app = Flask(__name__)

if not app.debug:
    # INFO logs
    handler = RotatingFileHandler("logs/info.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(Formatter(
        '%(asctime)s %(process)d %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(INFO)
    app.logger.addHandler(handler)

    # DEBUG logs
    handler = RotatingFileHandler("logs/debug.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(Formatter(
        '%(asctime)s %(process)d %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(DEBUG)
    app.logger.addHandler(handler)
    app.logger.setLevel(DEBUG)

# Need a special Jinja env for dealing with LaTeX
texenv = app.create_jinja_environment()
texenv.variable_start_string = '((('
texenv.variable_end_string = ')))'

languages = ('Python', 'Ruby', 'Java', 'C', 'C++', 'SQL', 'XML', 'HTML',
             'Haskell', 'Lisp', 'erlang', 'ABAP', 'ACSL', 'Ada', 'Algol',
             'Ant', 'Assembler', 'Awk', 'bash', 'Basic', 'Caml', 'CIL',
             'Clean', 'Cobol', 'Comal 80', 'command.com', 'Comsol',
             'csh', 'Delphi', 'Eiffel', 'Elan', 'Euphoria', 'Fortran',
             'GCL', 'Gnuplot', 'IDL', 'inform', 'JVMIS', 'ksh', 'Lingo',
             'Logo', 'make', 'Mathematica', 'Matlab', 'Mercury',
             'MetaPost', 'Miranda', 'Mizar', 'ML', 'Modula-2', 'MuPAD',
             'NASTRAN', 'Oberon-2', 'OCL', 'Octave', 'Oz', 'Pascal',
             'Perl', 'PHP', 'Pig', 'PL/I', 'Plasm', 'PostScript', 'POV',
             'Prolog', 'Promela', 'PSTricks', 'R', 'Reduce', 'Rexx',
             'RSL', 'S', 'SAS', 'Scilab', 'sh', 'SHELXL', 'Simula',
             'SPARQL', 'tcl', 'TeX', 'VBScript', 'Verilog', 'VHDL',
             'VRML', 'XSLT')

formats = ("png", "pdf", "jpg")

def convert_args(filename, alpha=False, background='#FFF'):
    args = shlex.split("convert -density 200 texput.pdf")
    if background:
        args += shlex.split("-background '%s'" % background)
    if not alpha:
        args += shlex.split("-flatten")
    args += shlex.split("-quality 90 %s" % filename)
    return args

class logger(object):
    @classmethod
    def debug(cls, msg, *args, **kwargs):
        msg = "[%s] %s" % (app.extensions['correlation_id'], msg)
        app.logger.debug(msg, *args, **kwargs)

    @classmethod
    def info(cls, msg, *args, **kwargs):
        msg = "[%s] %s" % (app.extensions['correlation_id'], msg)
        app.logger.info(msg, *args, **kwargs)

    @classmethod
    def warn(cls, msg, *args, **kwargs):
        msg = "[%s] %s" % (app.extensions['correlation_id'], msg)
        app.logger.warn(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg, *args, **kwargs):
        msg = "[%s] %s" % (app.extensions['correlation_id'], msg)
        app.logger.error(msg, *args, **kwargs)
        

@app.route("/")
def index():
    return render_template("index.html", 
        source=open("main.py").read(),
        languages=languages,
        formats=formats,
        extra_head=extras.head,
        extra_foot=extras.foot)

@app.route("/robots.txt")
def robots():
    resp = make_response("User-agent: *\nDisallow: /render")
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/render", methods=["POST"])
def render():
    lang = request.form['lang']
    source = request.form['source']
    mode = request.form['mode']
    fmt = request.form['format']
    background = str(request.form['background'])
    alpha = request.form.get('alpha','off') == "on"

    request_params = frozenset([lang, source, mode, fmt, background, alpha, time.time()])

    # Generate a correlation id for debugging
    app.extensions['correlation_id'] = hash(request_params)

    assert fmt in formats
    assert lang in languages

    background_rgb = hex_to_rgb(background)

    logger.info("Begin handle of request")

    wd = tempfile.mkdtemp()
    logger.info("Creating temp directory %s" % wd)

    # Sanitize the LaTeX source
    if '\end{lstlisting}' in source:
        source = source.replace('\end{lstlisting}', '%\\textbackslash)end{lstlisting}')

    latexTmpl = texenv.get_template("source-listing.tex")
    latexBody = latexTmpl.render(lang=lang, source=source)

    # Generate PDF
    standalone = os.path.join(os.getcwd(), "standalone")
    env = os.environ
    env["TEXINPUTS"] = ".:%s:" % standalone
    p1 = subprocess.Popen(["pdflatex"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
           cwd=wd, shell=True, env=env)
    (stdout, stderr) = p1.communicate(latexBody.encode('latin-1'))
    if p1.returncode != 0:
        logger.error("pdflatex had an error, check debug logs")
        logger.debug("pdflatex stdout: %s" % stdout)
        logger.debug("pdflatex stderr: %s" % stderr)

    if fmt == "pdf":
        fileBytes = open(os.path.join(wd, "texput.pdf"), "r").read()
        contentType = "application/pdf"
        fileName = "%s-listing.pdf" % lang.lower()
    # Convert with ImageMagick if request
    elif fmt == "png":
        args = convert_args("texput.png", alpha=alpha, background=background)
        p2 = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
        (stdout, stderr) = p2.communicate()
        if p2.returncode != 0:
            logger.error("convert had an error, check debug logs")
            logger.debug("convert stdout: %s" % stdout)
            logger.debug("convert stderr: %s" % stderr)
            abort(503)
        else:
            fileBytes = open(os.path.join(wd, "texput.png"), "r").read()
            contentType = "image/png"
            fileName = "%s-listing.png" % lang.lower()
    elif fmt == "jpg":
        args = convert_args("texput.jpg", alpha=False, background=background)
        p2 = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
        (stdout, stderr) = p2.communicate()
        if p2.returncode != 0:
            logger.error("convert had an error, check debug logs")
            logger.debug("convert stdout: %s" % stdout)
            logger.debug("convert stderr: %s" % stderr)
            abort(503)
        else:
            fileBytes = open(os.path.join(wd, "texput.jpg"), "r").read()
            contentType = "image/jpeg"
            fileName = "%s-listing.jpg" % lang.lower()

    resp = make_response(fileBytes)
    resp.headers["Content-Type"] = contentType

    if mode == "download":
        resp.headers["Content-Disposition"] = "attachment; filename=%s" % fileName

    logger.info("Removing %s" % wd)
    shutil.rmtree(wd)
    logger.info("End handle of request")
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

from cStringIO import StringIO
import logging
from logging import Formatter, StreamHandler, DEBUG, INFO
from logging.handlers import RotatingFileHandler
import os
import shutil
import tempfile
import time

from flask import Flask, abort, request, render_template, make_response

import extras
from render import render_pdf, convert

app = Flask(__name__)

# Configure logging
if not app.debug:
    logger = logging.getLogger("source2Image")
    logger.setLevel(DEBUG)
    app.logger.setLevel(DEBUG)
    formatter = Formatter('%(asctime)s %(process)d %(levelname)s: [%(correlation_id)s] '
                          '%(message)s [in %(pathname)s:%(lineno)d]')
    # INFO logs
    handler = RotatingFileHandler("logs/info.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(formatter)
    handler.setLevel(INFO)
    app.logger.addHandler(handler)
    logger.addHandler(handler)

    # DEBUG logs
    handler = RotatingFileHandler("logs/debug.log", maxBytes=1024*1024*32, backupCount=10)
    handler.setFormatter(formatter)
    handler.setLevel(DEBUG)
    app.logger.addHandler(handler)
    logger.addHandler(handler)

# Need a special Jinja env for dealing with LaTeX
texenv = app.create_jinja_environment()
texenv.variable_start_string = '((('
texenv.variable_end_string = ')))'

languages = ('Python', 'Ruby', 'Java', 'C', 'C++', 'SQL', 'XML', 'HTML',
             'Haskell', 'Lisp', 'erlang', 'Scala', 'ABAP', 'ACSL', 'Ada', 'Algol',
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

formats = ("png", "jpg", "pdf")

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html", 
        source="print(\"Hello, World\")",
        languages=languages,
        formats=formats,
        extra_head=extras.head,
        extra_foot=extras.foot)

@app.route("/robots.txt")
def robots():
    resp = make_response("User-agent: *\nAllow: /\nDisallow: /render")
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/render", methods=["POST"])
def render():
    t1 = time.time()
    lang = request.form['lang']
    source = request.form['source']
    mode = request.form['mode']
    fmt = request.form['format']
    background = str(request.form['background'])
    alpha = request.form.get('alpha','off') == "on"
    width = int(request.form['width'])
    height = int(request.form['height'])

    request_params = frozenset([lang, source, mode, fmt, background, alpha, time.time()])

    # Generate a correlation id for debugging
    app.extensions['correlation_id'] = hash(request_params)

    # Wrap the logger with some request context
    logger = logging.getLogger("source2Image")
    logger = logging.LoggerAdapter(logger, app.extensions)

    # Input validation
    assert fmt in formats
    assert lang in languages
    assert width <= 2048
    assert height <= 2048

    logger.info("Begin handle of request")

    wd = tempfile.mkdtemp()
    logger.info("Creating temp directory %s" % wd)

    # Sanitize the LaTeX source
    if '\end{lstlisting}' in source:
        source = source.replace('\end{lstlisting}', '%\\textbackslash)end{lstlisting}')

    latexTmpl = texenv.get_template("source-listing.tex")
    latexBody = latexTmpl.render(lang=lang, source=source)

    # Generate PDF
    pdfPath = render_pdf(latexBody, wd)
    if not pdfPath:
        abort(503)

    # Determine the correct output, convert with ImageMagick if necessary
    if fmt == "pdf":
        fileBytes = open(pdfPath, "r").read()
        contentType = "application/pdf"
        fileName = "%s-listing.pdf" % lang.lower()
    elif fmt == "png":
        outPath = convert(pdfPath, "texput.png", wd, 
                alpha=alpha, background=background, resize=(width, height))
        if not outPath:
            abort(503)
        else:
            fileBytes = open(outPath, "r").read()
            contentType = "image/png"
            fileName = "%s-listing.png" % lang.lower()
    elif fmt == "jpg":
        outPath = convert(pdfPath, "texput.jpg", wd,
                alpha=False, background=background, resize=(width, height))
        if not outPath:
            abort(503)
        else:
            fileBytes = open(outPath, "r").read()
            contentType = "image/jpeg"
            fileName = "%s-listing.jpg" % lang.lower()

    # Make the response
    resp = make_response(fileBytes)
    resp.headers["Content-Type"] = contentType

    if mode == "download":
        resp.headers["Content-Disposition"] = "attachment; filename=%s" % fileName

    logger.info("Removing %s" % wd)
    shutil.rmtree(wd)
    t2 = time.time()
    logger.info("End handle of request. Finished in %0.2fs" % (t2-t1))
    return resp

if __name__ == "__main__":
    logging.basicConfig(level=DEBUG)
    app.run(host="0.0.0.0", debug=True)

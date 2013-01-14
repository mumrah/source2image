from cStringIO import StringIO
import os
import shlex
import subprocess
import tempfile

from flask import Flask, request, render_template, make_response
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/render", methods=["POST"])
def render():
    lang = request.form['lang']
    source = request.form['source']
    wd = tempfile.mkdtemp()
    latexBody = render_template("source-listing.tex", lang=lang, source=source)
    inFile = StringIO(latexBody)
    p1 = subprocess.Popen(["pdflatex"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
    (stdout, stderr) = p1.communicate(latexBody)

    p2args = shlex.split("convert -density 300 texput.pdf -quality 90 texput.png")
    p2 = subprocess.Popen(p2args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
    (stdout, stderr) = p2.communicate()

    png = open(os.path.join(wd, "texput.png"), "r").read()
    resp = make_response(png)
    resp.headers["Content-Type"] = "image/png"
    #resp.headers["Content-Disposition"] = "attachment; filename=listing.png"
    return resp


if __name__ == "__main__":
    app.run()

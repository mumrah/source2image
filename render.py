import logging
import os
import shlex
import subprocess
import time

logger = logging.getLogger("source2image")

def render_pdf(latexSource, wd):
    # Generate PDF
    standalone = os.path.join(os.getcwd(), "standalone")
    env = os.environ
    env["TEXINPUTS"] = ".:%s:" % standalone
    t1 = time.time()
    proc = subprocess.Popen(shlex.split("pdflatex"), 
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=wd, shell=True, env=env
    )
    (stdout, stderr) = proc.communicate(latexSource.encode('latin-1', 'replace'))
    t2 = time.time()
    logger.info("Ran `pdflatex` in %0.2fs" % (t2-t1))
    
    if proc.returncode != 0:
        logger.error("pdflatex had an error, check debug logs")
        logger.debug("pdflatex stdout: %s" % stdout)
        logger.debug("pdflatex stderr: %s" % stderr)
        return None
    else:
        return os.path.join(wd, "texput.pdf")

def convert(pdfPath, outFileName, wd, alpha=False, background='#FFF'):
    args = shlex.split("convert -density 200 %s" % pdfPath)
    if background:
        args += shlex.split("-background '%s'" % background)
    if not alpha:
        args += shlex.split("-flatten")
    args += shlex.split("-quality 90 %s" % outFileName)
    t1 = time.time()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd)
    (stdout, stderr) = proc.communicate()
    t2 = time.time()
    logger.info("Ran `convert` in %0.2fs" % (t2-t1))

    if proc.returncode != 0:
        logger.error("convert had an error, check debug logs")
        logger.debug("convert stdout: %s" % stdout)
        logger.debug("convert stderr: %s" % stderr)
        return None
    else:
        return os.path.join(wd, outFileName)

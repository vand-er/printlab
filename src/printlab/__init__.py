import logging

# build123d warns about an unreadable Windows font (mstmc.ttf) on every Text(); it is noise.
logging.getLogger("build123d").addFilter(lambda record: "mstmc" not in record.getMessage())

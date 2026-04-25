"""
build_generation_map.py

Generates generation_map.json  — a mapping from every VMMRdb folder name
to a clean, human-readable "Make Model (Generation)" label.

Rules applied:
  - Trim variants (camry_le, camry_se, …) are consolidated to the base model.
  - Where enthusiasts use chassis codes (E46, W210, Mk4, NA…), those are used.
  - Where no popular code exists, "Nth Generation" is used.
  - Models with only one generation in the dataset get no generation suffix.
  - Year-1900 / year-1908 placeholder entries are flagged in a separate list.

Usage:
    python build_generation_map.py
Outputs:
    generation_map.json
    generation_map_unmapped.txt   (entries that had no matching rule)
"""

import json
import re
import os
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP TABLES
# Each entry: make_model_key -> [(year_start, year_end, "Display Label"), ...]
# The first matching range wins.
# ─────────────────────────────────────────────────────────────────────────────

BMW_MAP = {
    # ── 1 Series (E82/E88) ────────────────────────────────────────────────────
    "bmw_128i": [(2008, 2013, "BMW 1 Series (E82/E88)")],
    "bmw_135i": [(2008, 2011, "BMW 1 Series (E82/E88)")],
    "bmw_135i_convertible": [(2010, 2010, "BMW 1 Series (E88)")],
    # ── 3 Series ──────────────────────────────────────────────────────────────
    "bmw_318i": [
        (1984, 1991, "BMW 3 Series (E30)"),
        (1992, 1998, "BMW 3 Series (E36)"),
    ],
    "bmw_318i_convertible": [(1994, 1996, "BMW 3 Series (E36)")],
    "bmw_320i": [
        (1979, 1983, "BMW 3 Series (E21)"),
        (1984, 1990, "BMW 3 Series (E30)"),
        (1991, 1998, "BMW 3 Series (E36)"),
        (1999, 2005, "BMW 3 Series (E46)"),
        (2006, 2011, "BMW 3 Series (E9x)"),
        (2012, 2014, "BMW 3 Series (F30)"),
    ],
    "bmw_323i": [
        (1980, 1982, "BMW 3 Series (E21)"),
        (1983, 1990, "BMW 3 Series (E30)"),
        (1991, 1999, "BMW 3 Series (E36)"),
        (2000, 2006, "BMW 3 Series (E46)"),
        (2007, 2011, "BMW 3 Series (E9x)"),
    ],
    "bmw_325ci": [(2001, 2004, "BMW 3 Series (E46)")],
    "bmw_325e": [
        (1984, 1991, "BMW 3 Series (E30)"),
        (1992, 1998, "BMW 3 Series (E36)"),
    ],
    "bmw_325es": [(1986, 1986, "BMW 3 Series (E30)")],
    "bmw_325i": [
        (1979, 1983, "BMW 3 Series (E21)"),
        (1984, 1991, "BMW 3 Series (E30)"),
        (1992, 1999, "BMW 3 Series (E36)"),
        (2000, 2005, "BMW 3 Series (E46)"),
        (2006, 2013, "BMW 3 Series (E9x)"),
    ],
    "bmw_325i_wagon": [(2001, 2005, "BMW 3 Series (E46)")],
    "bmw_325is": [
        (1987, 1991, "BMW 3 Series (E30)"),
        (1992, 1994, "BMW 3 Series (E36)"),
    ],
    "bmw_325xi": [
        (2002, 2005, "BMW 3 Series (E46)"),
        (2006, 2006, "BMW 3 Series (E9x)"),
    ],
    "bmw_325xi_wagon": [(2002, 2002, "BMW 3 Series (E46)")],
    "bmw_328i": [
        (1995, 1999, "BMW 3 Series (E36)"),
        (2000, 2006, "BMW 3 Series (E46)"),
        (2007, 2011, "BMW 3 Series (E9x)"),
        (2012, 2014, "BMW 3 Series (F30)"),
    ],
    "bmw_328ic": [
        (1997, 1999, "BMW 3 Series (E36)"),
        (2000, 2006, "BMW 3 Series (E46)"),
        (2007, 2010, "BMW 3 Series (E9x)"),
    ],
    "bmw_328is": [
        (1996, 1999, "BMW 3 Series (E36)"),
        (2000, 2006, "BMW 3 Series (E46)"),
        (2007, 2008, "BMW 3 Series (E9x)"),
    ],
    "bmw_328xi": [
        (2006, 2011, "BMW 3 Series (E9x)"),
        (2012, 2013, "BMW 3 Series (F30)"),
    ],
    "bmw_330ci": [(2001, 2006, "BMW 3 Series (E46)")],
    "bmw_330i": [
        (2001, 2005, "BMW 3 Series (E46)"),
        (2006, 2006, "BMW 3 Series (E9x)"),
    ],
    "bmw_330xi": [
        (2002, 2005, "BMW 3 Series (E46)"),
        (2006, 2006, "BMW 3 Series (E9x)"),
    ],
    "bmw_335i": [
        (2001, 2006, "BMW 3 Series (E46)"),
        (2007, 2013, "BMW 3 Series (E9x)"),
        (2014, 2015, "BMW 3 Series (F30)"),
    ],
    "bmw_335xi": [(2007, 2008, "BMW 3 Series (E9x)")],
    "bmw_3series": [
        (1991, 1999, "BMW 3 Series (E36)"),
        (2000, 2006, "BMW 3 Series (E46)"),
        (2007, 2013, "BMW 3 Series (E9x)"),
    ],
    "bmw_e30": [(1987, 1992, "BMW 3 Series (E30)")],
    "bmw_e36": [(1992, 1999, "BMW 3 Series (E36)")],
    "bmw_e46": [(2000, 2005, "BMW 3 Series (E46)")],
    "bmw_e93": [(2007, 2007, "BMW 3 Series (E9x)")],
    # ── 4 Series (F32/F33) ────────────────────────────────────────────────────
    "bmw_428i": [(2014, 2015, "BMW 4 Series (F32/F33)")],
    "bmw_435i": [(2015, 2015, "BMW 4 Series (F32/F33)")],
    # ── 5 Series ──────────────────────────────────────────────────────────────
    "bmw_523i": [(2008, 2008, "BMW 5 Series (E60)")],
    "bmw_525i": [
        (1989, 1995, "BMW 5 Series (E34)"),
        (1996, 2003, "BMW 5 Series (E39)"),
        (2004, 2007, "BMW 5 Series (E60)"),
    ],
    "bmw_525xi": [(2006, 2006, "BMW 5 Series (E60)")],
    "bmw_528": [(2013, 2013, "BMW 5 Series (F10)")],
    "bmw_528e": [(1983, 1987, "BMW 5 Series (E28)")],
    "bmw_528i": [
        (1967, 1980, "BMW 5 Series (E12)"),
        (1981, 1987, "BMW 5 Series (E28)"),
        (1988, 1995, "BMW 5 Series (E34)"),
        (1996, 2003, "BMW 5 Series (E39)"),
        (2004, 2009, "BMW 5 Series (E60)"),
        (2010, 2013, "BMW 5 Series (F10)"),
    ],
    "bmw_528xi": [(2008, 2009, "BMW 5 Series (E60)")],
    "bmw_530i": [
        (1988, 1995, "BMW 5 Series (E34)"),
        (1996, 2003, "BMW 5 Series (E39)"),
        (2004, 2008, "BMW 5 Series (E60)"),
    ],
    "bmw_530xi": [(2006, 2007, "BMW 5 Series (E60)")],
    "bmw_530xi_wagon": [(2006, 2006, "BMW 5 Series (E60)")],
    "bmw_535i": [
        (1985, 1988, "BMW 5 Series (E28)"),
        (1989, 1995, "BMW 5 Series (E34)"),
        (1996, 2003, "BMW 5 Series (E39)"),
        (2004, 2010, "BMW 5 Series (E60)"),
        (2011, 2013, "BMW 5 Series (F10)"),
    ],
    "bmw_535xi": [(2008, 2009, "BMW 5 Series (E60)")],
    "bmw_538i": [(1998, 1998, "BMW 5 Series (E39)")],   # mislabeled model
    "bmw_539i": [(2003, 2003, "BMW 5 Series (E39)")],   # mislabeled model
    "bmw_540i": [
        (1992, 1995, "BMW 5 Series (E34)"),
        (1996, 2004, "BMW 5 Series (E39)"),
    ],
    "bmw_545i": [(2004, 2005, "BMW 5 Series (E60)")],
    "bmw_550i": [
        (2006, 2010, "BMW 5 Series (E60)"),
        (2011, 2013, "BMW 5 Series (F10)"),
    ],
    "bmw_5series": [
        (1998, 2003, "BMW 5 Series (E39)"),
        (2004, 2007, "BMW 5 Series (E60)"),
    ],
    "bmw_e39": [(2002, 2002, "BMW 5 Series (E39)")],
    # ── 6 Series ──────────────────────────────────────────────────────────────
    "bmw_633csi": [(1984, 1984, "BMW 6 Series (E24)")],
    "bmw_635csi": [(1978, 1989, "BMW 6 Series (E24)")],
    "bmw_640i": [(2014, 2014, "BMW 6 Series (F12/F13)")],
    "bmw_645ci": [(2004, 2005, "BMW 6 Series (E63/E64)")],
    "bmw_645i": [(2004, 2004, "BMW 6 Series (E63/E64)")],
    "bmw_650i": [
        (2004, 2010, "BMW 6 Series (E63/E64)"),
        (2011, 2014, "BMW 6 Series (F12/F13)"),
    ],
    "bmw_650i_convertible": [(2012, 2012, "BMW 6 Series (F12)")],
    # ── 7 Series ──────────────────────────────────────────────────────────────
    "bmw_730i": [(2005, 2005, "BMW 7 Series (E65/E66)")],
    "bmw_733i": [(1979, 1984, "BMW 7 Series (E23)")],
    "bmw_735i": [
        (1985, 1987, "BMW 7 Series (E23)"),
        (1988, 1991, "BMW 7 Series (E32)"),
    ],
    "bmw_740i": [
        (1993, 1994, "BMW 7 Series (E32)"),
        (1995, 2001, "BMW 7 Series (E38)"),
        (2002, 2008, "BMW 7 Series (E65/E66)"),
        (2009, 2013, "BMW 7 Series (F01)"),
    ],
    "bmw_745i": [
        (1984, 1986, "BMW 7 Series (E23)"),
        (1987, 1994, "BMW 7 Series (E32)"),
        (1995, 2001, "BMW 7 Series (E38)"),
        (2002, 2005, "BMW 7 Series (E65/E66)"),
    ],
    "bmw_750i": [
        (1990, 1994, "BMW 7 Series (E32)"),
        (1995, 2001, "BMW 7 Series (E38)"),
        (2002, 2008, "BMW 7 Series (E65/E66)"),
        (2009, 2014, "BMW 7 Series (F01)"),
    ],
    "bmw_760i": [(2003, 2006, "BMW 7 Series (E65/E66)")],
    "bmw_7series": [
        (1996, 2001, "BMW 7 Series (E38)"),
        (2002, 2008, "BMW 7 Series (E65/E66)"),
        (2009, 2013, "BMW 7 Series (F01)"),
    ],
    # ── 8 Series (E31) ────────────────────────────────────────────────────────
    "bmw_840ci": [(1995, 1995, "BMW 8 Series (E31)")],
    "bmw_850ci": [(1993, 1996, "BMW 8 Series (E31)")],
    "bmw_850i": [(1991, 1992, "BMW 8 Series (E31)")],
    # ── M Models ──────────────────────────────────────────────────────────────
    "bmw_m3": [
        (1988, 1991, "BMW M3 (E30)"),
        (1992, 1999, "BMW M3 (E36)"),
        (2000, 2006, "BMW M3 (E46)"),
        (2007, 2013, "BMW M3 (E9x)"),
    ],
    "bmw_m3_convertible": [
        (2004, 2006, "BMW M3 (E46)"),
        (2007, 2008, "BMW M3 (E9x)"),
    ],
    "bmw_m5": [
        (1999, 2003, "BMW M5 (E39)"),
        (2004, 2010, "BMW M5 (E60)"),
        (2011, 2013, "BMW M5 (F10)"),
    ],
    "bmw_m6": [(2006, 2010, "BMW M6 (E63/E64)")],
    "bmw_m_roadster": [(1998, 2000, "BMW M Roadster (E36/7)")],
    # ── X Models ──────────────────────────────────────────────────────────────
    "bmw_x1": [(2013, 2014, "BMW X1 (E84)")],
    "bmw_x3": [
        (2004, 2010, "BMW X3 (E83)"),
        (2011, 2012, "BMW X3 (F25)"),
    ],
    "bmw_x5": [
        (2000, 2006, "BMW X5 (E53)"),
        (2007, 2014, "BMW X5 (E70)"),
    ],
    "bmw_e53": [(2004, 2004, "BMW X5 (E53)")],
    "bmw_x6": [(2012, 2013, "BMW X6 (E71)")],
    # ── Z Models ──────────────────────────────────────────────────────────────
    "bmw_z3": [
        (1996, 2002, "BMW Z3 (E36/7)"),
        (2003, 2004, "BMW Z4 (E85)"),  # Z3 ended 2002; late entries are Z4
    ],
    "bmw_z4": [
        (2003, 2008, "BMW Z4 (E85/E86)"),
        (2009, 2011, "BMW Z4 (E89)"),
    ],
    # ── Electric ──────────────────────────────────────────────────────────────
    "bmw_i3": [(2014, 2014, "BMW i3 (I01)")],
}

MERCEDES_MAP = {
    # ── 190 / W201 ────────────────────────────────────────────────────────────
    "mercedes benz_190": [(1982, 1993, "Mercedes-Benz 190 (W201)")],
    "mercedes benz_190d": [
        (1961, 1968, "Mercedes-Benz 190D (W110)"),
        (1969, 1976, "Mercedes-Benz 190D (W115)"),
        (1977, 1993, "Mercedes-Benz 190D (W201)"),
    ],
    # ── Diesel sedans (W115/W123) ─────────────────────────────────────────────
    "mercedes benz_220d": [(1968, 1976, "Mercedes-Benz 220D (W115)")],
    "mercedes benz_240d": [
        (1974, 1976, "Mercedes-Benz 240D (W115)"),
        (1977, 1985, "Mercedes-Benz 240D (W123)"),
    ],
    "mercedes benz_300d": [
        (1976, 1985, "Mercedes-Benz 300D (W123)"),
        (1986, 1996, "Mercedes-Benz 300D (W124)"),
    ],
    # ── B-Class (W245) ────────────────────────────────────────────────────────
    "mercedes benz_b200": [(2005, 2011, "Mercedes-Benz B-Class (W245)")],
    "mercedes benz_b200t": [(2005, 2011, "Mercedes-Benz B-Class (W245)")],
    # ── C-Class ───────────────────────────────────────────────────────────────
    "mercedes benz_c220": [(1993, 2000, "Mercedes-Benz C-Class (W202)")],
    "mercedes benz_c230": [
        (1993, 2000, "Mercedes-Benz C-Class (W202)"),
        (2001, 2007, "Mercedes-Benz C-Class (W203)"),
        (2008, 2013, "Mercedes-Benz C-Class (W204)"),
    ],
    "mercedes benz_c240": [(2000, 2007, "Mercedes-Benz C-Class (W203)")],
    "mercedes benz_c250": [
        (2007, 2014, "Mercedes-Benz C-Class (W204)"),
        (2015, 2021, "Mercedes-Benz C-Class (W205)"),
    ],
    "mercedes benz_c280": [
        (1993, 2000, "Mercedes-Benz C-Class (W202)"),
        (2001, 2007, "Mercedes-Benz C-Class (W203)"),
    ],
    "mercedes benz_c300": [
        (1982, 1993, "Mercedes-Benz 190 (W201)"),   # 1988 entry mislabeled
        (2007, 2014, "Mercedes-Benz C-Class (W204)"),
    ],
    "mercedes benz_c32": [(2000, 2007, "Mercedes-Benz C-Class (W203)")],
    "mercedes benz_c320": [(2000, 2007, "Mercedes-Benz C-Class (W203)")],
    "mercedes benz_c350": [
        (2000, 2007, "Mercedes-Benz C-Class (W203)"),
        (2008, 2014, "Mercedes-Benz C-Class (W204)"),
    ],
    "mercedes benz_c55": [(2000, 2007, "Mercedes-Benz C-Class (W203)")],
    # ── Coupe variants (C123 / C124) ─────────────────────────────────────────
    "mercedes benz_cd300": [(1976, 1985, "Mercedes-Benz E-Class Coupe (C123)")],
    "mercedes benz_ce300": [(1987, 1997, "Mercedes-Benz E-Class Coupe (C124)")],
    # ── CL (S-Class coupe) ────────────────────────────────────────────────────
    "mercedes benz_cl500": [(1999, 2006, "Mercedes-Benz CL-Class (C215)")],
    "mercedes benz_cl550": [(2006, 2013, "Mercedes-Benz CL-Class (C216)")],
    "mercedes benz_cl600": [(1999, 2006, "Mercedes-Benz CL-Class (C215)")],
    # ── CLA (C117) ────────────────────────────────────────────────────────────
    "mercedes benz_cla250": [(2013, 2019, "Mercedes-Benz CLA-Class (C117)")],
    # ── CLK ───────────────────────────────────────────────────────────────────
    "mercedes benz_clk240": [(2002, 2009, "Mercedes-Benz CLK-Class (W209)")],
    "mercedes benz_clk320": [
        (1997, 2002, "Mercedes-Benz CLK-Class (W208)"),
        (2003, 2009, "Mercedes-Benz CLK-Class (W209)"),
    ],
    "mercedes benz_clk350": [
        (1997, 2002, "Mercedes-Benz CLK-Class (W208)"),
        (2003, 2009, "Mercedes-Benz CLK-Class (W209)"),
    ],
    "mercedes benz_clk430": [(1997, 2002, "Mercedes-Benz CLK-Class (W208)")],
    "mercedes benz_clk500": [
        (1997, 2002, "Mercedes-Benz CLK-Class (W208)"),
        (2003, 2009, "Mercedes-Benz CLK-Class (W209)"),
    ],
    "mercedes benz_clk55": [
        (1997, 2002, "Mercedes-Benz CLK-Class (W208)"),
        (2003, 2009, "Mercedes-Benz CLK-Class (W209)"),
    ],
    "mercedes benz_clk550": [(2002, 2009, "Mercedes-Benz CLK-Class (W209)")],
    # ── CLS ───────────────────────────────────────────────────────────────────
    "mercedes benz_cls500": [(2004, 2010, "Mercedes-Benz CLS-Class (C219)")],
    "mercedes benz_cls550": [
        (2004, 2010, "Mercedes-Benz CLS-Class (C219)"),
        (2011, 2018, "Mercedes-Benz CLS-Class (C218)"),
    ],
    # ── E-Class ───────────────────────────────────────────────────────────────
    "mercedes benz_e190": [(1982, 1993, "Mercedes-Benz 190 (W201)")],
    "mercedes benz_e300": [
        (1984, 1995, "Mercedes-Benz E-Class (W124)"),
        (1996, 2002, "Mercedes-Benz E-Class (W210)"),
        (2003, 2009, "Mercedes-Benz E-Class (W211)"),
    ],
    "mercedes benz_e320": [
        (1984, 1995, "Mercedes-Benz E-Class (W124)"),
        (1996, 2002, "Mercedes-Benz E-Class (W210)"),
        (2003, 2009, "Mercedes-Benz E-Class (W211)"),
    ],
    "mercedes benz_e320_wagon": [
        (1984, 1995, "Mercedes-Benz E-Class Wagon (S124)"),
        (1996, 2002, "Mercedes-Benz E-Class Wagon (S210)"),
    ],
    "mercedes benz_e350": [
        (2002, 2009, "Mercedes-Benz E-Class (W211)"),
        (2010, 2016, "Mercedes-Benz E-Class (W212)"),
    ],
    "mercedes benz_e350_wagon": [
        (1996, 2002, "Mercedes-Benz E-Class Wagon (S210)"),
        (2010, 2016, "Mercedes-Benz E-Class Wagon (S212)"),
    ],
    "mercedes benz_e420": [
        (1984, 1995, "Mercedes-Benz E-Class (W124)"),
        (1996, 2002, "Mercedes-Benz E-Class (W210)"),
    ],
    "mercedes benz_e430": [(1996, 2002, "Mercedes-Benz E-Class (W210)")],
    "mercedes benz_e500": [
        (1984, 1995, "Mercedes-Benz E-Class (W124)"),
        (1996, 2002, "Mercedes-Benz E-Class (W210)"),
        (2003, 2009, "Mercedes-Benz E-Class (W211)"),
    ],
    "mercedes benz_e55": [
        (1996, 2002, "Mercedes-Benz E-Class (W210)"),
        (2003, 2009, "Mercedes-Benz E-Class (W211)"),
    ],
    "mercedes benz_e550": [
        (2002, 2009, "Mercedes-Benz E-Class (W211)"),
        (2010, 2016, "Mercedes-Benz E-Class (W212)"),
    ],
    "mercedes benz_e63": [
        (2002, 2009, "Mercedes-Benz E-Class (W211)"),
        (2010, 2016, "Mercedes-Benz E-Class (W212)"),
    ],
    # ── GL-Class ──────────────────────────────────────────────────────────────
    "mercedes benz_gl320": [(2006, 2012, "Mercedes-Benz GL-Class (X164)")],
    "mercedes benz_gl350": [(2012, 2019, "Mercedes-Benz GL-Class (X166)")],
    "mercedes benz_gl450": [(2006, 2012, "Mercedes-Benz GL-Class (X164)")],
    "mercedes benz_gl550": [(2006, 2012, "Mercedes-Benz GL-Class (X164)")],
    # ── GLA-Class (X156) ──────────────────────────────────────────────────────
    "mercedes benz_gla250": [(2013, 2019, "Mercedes-Benz GLA-Class (X156)")],
    "mercedes benz_gla45": [(2013, 2019, "Mercedes-Benz GLA-Class (X156)")],
    # ── GLK-Class (X204) ──────────────────────────────────────────────────────
    "mercedes benz_glk350": [(2008, 2015, "Mercedes-Benz GLK-Class (X204)")],
    # ── M-Class ───────────────────────────────────────────────────────────────
    "mercedes benz_ml320": [
        (1997, 2005, "Mercedes-Benz M-Class (W163)"),
        (2006, 2011, "Mercedes-Benz M-Class (W164)"),
    ],
    "mercedes benz_ml350": [
        (1997, 2005, "Mercedes-Benz M-Class (W163)"),
        (2006, 2011, "Mercedes-Benz M-Class (W164)"),
        (2012, 2015, "Mercedes-Benz M-Class (W166)"),
    ],
    "mercedes benz_ml430": [(1997, 2005, "Mercedes-Benz M-Class (W163)")],
    "mercedes benz_ml500": [
        (1997, 2005, "Mercedes-Benz M-Class (W163)"),
        (2006, 2011, "Mercedes-Benz M-Class (W164)"),
    ],
    "mercedes benz_ml55": [(1997, 2005, "Mercedes-Benz M-Class (W163)")],
    "mercedes benz_ml550": [(2006, 2011, "Mercedes-Benz M-Class (W164)")],
    # ── R-Class (W251) ────────────────────────────────────────────────────────
    "mercedes benz_r350": [(2005, 2013, "Mercedes-Benz R-Class (W251)")],
    "mercedes benz_r500": [(2005, 2013, "Mercedes-Benz R-Class (W251)")],
    # ── S-Class ───────────────────────────────────────────────────────────────
    "mercedes benz_s280": [(1965, 1972, "Mercedes-Benz S-Class (W108/W109)")],
    "mercedes benz_s320": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
    ],
    "mercedes benz_s350": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
        (2006, 2013, "Mercedes-Benz S-Class (W221)"),
    ],
    "mercedes benz_s420": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
    ],
    "mercedes benz_s430": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
    ],
    "mercedes benz_s500": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
    ],
    "mercedes benz_s55": [(1999, 2005, "Mercedes-Benz S-Class (W220)")],
    "mercedes benz_s550": [
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
        (2006, 2013, "Mercedes-Benz S-Class (W221)"),
    ],
    "mercedes benz_s600": [
        (1991, 1998, "Mercedes-Benz S-Class (W140)"),
        (1999, 2005, "Mercedes-Benz S-Class (W220)"),
        (2006, 2013, "Mercedes-Benz S-Class (W221)"),
    ],
    "mercedes benz_s65": [(2006, 2013, "Mercedes-Benz S-Class (W221)")],
    # ── S-Class variants (SE/SEL/SD/SDL) ─────────────────────────────────────
    "mercedes benz_sd300": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_sdl300": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_se280": [
        (1965, 1972, "Mercedes-Benz S-Class (W108/W109)"),
        (1973, 1980, "Mercedes-Benz S-Class (W116)"),
    ],
    "mercedes benz_se380": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_se400": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_se450": [(1972, 1980, "Mercedes-Benz S-Class (W116)")],
    "mercedes benz_sel300": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_sel400": [(1991, 1998, "Mercedes-Benz S-Class (W140)")],
    "mercedes benz_sel420": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    "mercedes benz_sel450": [(1972, 1980, "Mercedes-Benz S-Class (W116)")],
    "mercedes benz_sel600": [(1979, 1992, "Mercedes-Benz S-Class (W126)")],
    # ── SL ────────────────────────────────────────────────────────────────────
    "mercedes benz_sl300": [
        (1971, 1989, "Mercedes-Benz SL-Class (R107)"),
        (1990, 2001, "Mercedes-Benz SL-Class (R129)"),
    ],
    "mercedes benz_sl320": [(1989, 2001, "Mercedes-Benz SL-Class (R129)")],
    "mercedes benz_sl380": [(1971, 1989, "Mercedes-Benz SL-Class (R107)")],
    "mercedes benz_sl450": [(1971, 1989, "Mercedes-Benz SL-Class (R107)")],
    "mercedes benz_sl500": [
        (1971, 1989, "Mercedes-Benz SL-Class (R107)"),
        (1990, 2001, "Mercedes-Benz SL-Class (R129)"),
        (2002, 2012, "Mercedes-Benz SL-Class (R230)"),
    ],
    "mercedes benz_sl55": [(2001, 2012, "Mercedes-Benz SL-Class (R230)")],
    "mercedes benz_sl550": [(2001, 2012, "Mercedes-Benz SL-Class (R230)")],
    "mercedes benz_sl560": [(1971, 1989, "Mercedes-Benz SL-Class (R107)")],
    "mercedes benz_sl600": [
        (1989, 2001, "Mercedes-Benz SL-Class (R129)"),
        (2002, 2012, "Mercedes-Benz SL-Class (R230)"),
    ],
    # ── SLC (R107 coupe) ──────────────────────────────────────────────────────
    "mercedes benz_slc450": [(1971, 1981, "Mercedes-Benz SLC-Class (R107)")],
    # ── SLK ───────────────────────────────────────────────────────────────────
    "mercedes benz_slk230": [
        (1996, 2004, "Mercedes-Benz SLK-Class (R170)"),
        (2005, 2011, "Mercedes-Benz SLK-Class (R171)"),
    ],
    "mercedes benz_slk280": [(2004, 2011, "Mercedes-Benz SLK-Class (R171)")],
    "mercedes benz_slk320": [(1996, 2004, "Mercedes-Benz SLK-Class (R170)")],
    "mercedes benz_slk350": [
        (1996, 2004, "Mercedes-Benz SLK-Class (R170)"),
        (2005, 2011, "Mercedes-Benz SLK-Class (R171)"),
    ],
    "mercedes benz_slk55": [(2004, 2011, "Mercedes-Benz SLK-Class (R171)")],
    # ── SLR / Sprinter / TD300 ────────────────────────────────────────────────
    "mercedes benz_slr": [(2003, 2010, "Mercedes-Benz SLR McLaren (C199)")],
    "mercedes benz_sprinter": [
        (1995, 2006, "Mercedes-Benz Sprinter (1st Generation)"),
        (2007, 2018, "Mercedes-Benz Sprinter (2nd Generation)"),
    ],
    "mercedes benz_td300": [(1977, 1986, "Mercedes-Benz 300TD (S123)")],
}

EUROPEAN_MAP = {
    # ── AUDI ──────────────────────────────────────────────────────────────────
    "audi_100": [
        (1989, 1990, "Audi 100 (C3)"),
        (1991, 1994, "Audi 100 (C4)"),
    ],
    "audi_80": [(1990, 1990, "Audi 80 (B3)")],
    "audi_90": [
        (1989, 1991, "Audi 90 (B3)"),
        (1992, 1993, "Audi 90 (B4)"),
    ],
    "audi_a3": [
        (2004, 2012, "Audi A3 (8P)"),
        (2013, 2015, "Audi A3 (8V)"),
    ],
    "audi_a4": [
        (1996, 2001, "Audi A4 (B5)"),
        (2002, 2005, "Audi A4 (B6)"),
        (2006, 2008, "Audi A4 (B7)"),
        (2009, 2014, "Audi A4 (B8)"),
    ],
    "audi_a4_avant": [
        (2006, 2008, "Audi A4 Avant (B7)"),
        (2009, 2012, "Audi A4 Avant (B8)"),
    ],
    "audi_a4_avant_wagon": [(2001, 2001, "Audi A4 Avant (B5)")],
    "audi_a4_cabriolet": [
        (1994, 2001, "Audi A4 Cabriolet (B5)"),
        (2002, 2005, "Audi A4 Cabriolet (B6)"),
        (2006, 2009, "Audi A4 Cabriolet (B7)"),
    ],
    "audi_a4_wagon": [
        (2004, 2005, "Audi A4 Avant (B6)"),
        (2006, 2006, "Audi A4 Avant (B7)"),
    ],
    "audi_a5": [(2008, 2015, "Audi A5 (8T)")],
    "audi_a5_cabriolet": [(2011, 2011, "Audi A5 Cabriolet (8T)")],
    "audi_a6": [
        (1995, 1997, "Audi A6 (C4)"),
        (1998, 2004, "Audi A6 (C5)"),
        (2005, 2011, "Audi A6 (C6)"),
        (2012, 2015, "Audi A6 (C7)"),
    ],
    "audi_a6_quattro": [(1999, 2000, "Audi A6 Quattro (C5)")],
    "audi_a6_quattro_wagon": [(2001, 2001, "Audi A6 Avant Quattro (C5)")],
    "audi_a7": [(2011, 2011, "Audi A7 (C7)")],
    "audi_a8": [
        (1997, 2002, "Audi A8 (D2)"),
        (2003, 2009, "Audi A8 (D3)"),
        (2010, 2013, "Audi A8 (D4)"),
    ],
    "audi_allroad": [
        (2001, 2006, "Audi Allroad Quattro (C5)"),
        (2013, 2014, "Audi Allroad (B8)"),
    ],
    "audi_cabriolet": [(1991, 2000, "Audi Cabriolet (B4)")],
    "audi_q5": [(2009, 2015, "Audi Q5 (8R)")],
    "audi_q7": [(2007, 2013, "Audi Q7 (4L)")],
    "audi_r8": [(2005, 2015, "Audi R8 (Type 42)")],
    "audi_rs4": [(2005, 2008, "Audi RS4 (B7)")],
    "audi_s3": [
        (2001, 2003, "Audi S3 (8L)"),
        (2006, 2012, "Audi S3 (8P)"),
        (2013, 2015, "Audi S3 (8V)"),
    ],
    "audi_s4": [
        (1993, 1994, "Audi S4 (B4)"),
        (1997, 2002, "Audi S4 (B5)"),
        (2003, 2005, "Audi S4 (B6)"),
        (2006, 2008, "Audi S4 (B7)"),
        (2009, 2014, "Audi S4 (B8)"),
    ],
    "audi_s4_avant": [(2005, 2005, "Audi S4 Avant (B7)")],
    "audi_s5": [(2008, 2013, "Audi S5 (8T)")],
    "audi_s6": [
        (1995, 1997, "Audi S6 (C4)"),
        (1999, 2004, "Audi S6 (C5)"),
        (2006, 2011, "Audi S6 (C6)"),
        (2012, 2013, "Audi S6 (C7)"),
    ],
    "audi_s8": [
        (2003, 2010, "Audi S8 (D3)"),
        (2011, 2014, "Audi S8 (D4)"),
    ],
    "audi_tt": [
        (2000, 2006, "Audi TT (Mk1/8N)"),
        (2007, 2014, "Audi TT (Mk2/8J)"),
        (2015, 2016, "Audi TT (Mk3/8S)"),
    ],
    # ── PORSCHE ───────────────────────────────────────────────────────────────
    "porsche_911": [
        (1974, 1988, "Porsche 911 (930)"),
        (1989, 1993, "Porsche 911 (964)"),
        (1994, 1997, "Porsche 911 (993)"),
        (1998, 2004, "Porsche 911 (996)"),
        (2005, 2012, "Porsche 911 (997)"),
        (2013, 2013, "Porsche 911 (991)"),
    ],
    "porsche_912": [(1976, 1976, "Porsche 912E")],
    "porsche_914": [(1970, 1976, "Porsche 914")],
    "porsche_917": [(1976, 1976, "Porsche 917")],
    "porsche_924": [(1976, 1988, "Porsche 924")],
    "porsche_928": [(1977, 1995, "Porsche 928")],
    "porsche_930": [(1975, 1989, "Porsche 911 Turbo (930)")],
    "porsche_944": [(1982, 1991, "Porsche 944")],
    "porsche_997": [(2005, 2012, "Porsche 911 (997)")],
    "porsche_boxster": [
        (1997, 2004, "Porsche Boxster (986)"),
        (2005, 2012, "Porsche Boxster (987)"),
        (2013, 2016, "Porsche Boxster (981)"),
    ],
    "porsche_cayenne": [
        (2002, 2010, "Porsche Cayenne (9PA)"),
        (2011, 2017, "Porsche Cayenne (92A)"),
    ],
    "porsche_cayman": [
        (2005, 2012, "Porsche Cayman (987c)"),
        (2013, 2016, "Porsche Cayman (981c)"),
    ],
    "porsche_panamera": [(2009, 2016, "Porsche Panamera (970)")],
    # ── VOLKSWAGEN ────────────────────────────────────────────────────────────
    "volkswagen_atlantic": [(1980, 1987, "Volkswagen Atlantic (Mk2)")],
    "volkswagen_beetle": [
        (1957, 2003, "Volkswagen Beetle (Type 1)"),
        (2004, 2010, "Volkswagen New Beetle (A4)"),
        (2011, 2015, "Volkswagen Beetle (A5)"),
    ],
    "volkswagen_bug": [
        (1957, 2003, "Volkswagen Beetle (Type 1)"),
        (2004, 2010, "Volkswagen New Beetle (A4)"),
        (2011, 2014, "Volkswagen Beetle (A5)"),
    ],
    "volkswagen_bus": [
        (1955, 1967, "Volkswagen Bus (T1)"),
        (1968, 1979, "Volkswagen Bus (T2)"),
        (1980, 1991, "Volkswagen Bus (T3)"),
    ],
    "volkswagen_cabrio": [(1995, 2002, "Volkswagen Cabrio (Mk3)")],
    "volkswagen_cabriolet": [
        (1985, 1993, "Volkswagen Cabriolet (Mk1)"),
        (1994, 2002, "Volkswagen Cabriolet (Mk3)"),
    ],
    "volkswagen_camper": [
        (1950, 1967, "Volkswagen Camper (T1)"),
        (1968, 1979, "Volkswagen Camper (T2)"),
        (1980, 1991, "Volkswagen Camper (T3)"),
        (1992, 2003, "Volkswagen Camper (T4)"),
    ],
    "volkswagen_cc": [(2009, 2017, "Volkswagen CC (B6)")],
    "volkswagen_corrado": [(1988, 1995, "Volkswagen Corrado")],
    "volkswagen_dunebuggy": [(1961, 1980, "Volkswagen Dune Buggy (Type 1)")],
    "volkswagen_eos": [(2006, 2015, "Volkswagen Eos (1F)")],
    "volkswagen_eurovan": [(1992, 2003, "Volkswagen EuroVan (T4)")],
    "volkswagen_fox": [(1987, 1993, "Volkswagen Fox")],
    "volkswagen_golf": [
        (1974, 1984, "Volkswagen Golf (Mk1)"),
        (1985, 1992, "Volkswagen Golf (Mk2)"),
        (1993, 1998, "Volkswagen Golf (Mk3)"),
        (1999, 2006, "Volkswagen Golf (Mk4)"),
        (2007, 2009, "Volkswagen Golf (Mk5)"),
        (2010, 2014, "Volkswagen Golf (Mk6)"),
    ],
    "volkswagen_gti": [
        (1983, 1984, "Volkswagen GTI (Mk1)"),
        (1985, 1992, "Volkswagen GTI (Mk2)"),
        (1993, 1998, "Volkswagen GTI (Mk3)"),
        (1999, 2005, "Volkswagen GTI (Mk4)"),
        (2006, 2009, "Volkswagen GTI (Mk5)"),
        (2010, 2015, "Volkswagen GTI (Mk6)"),
    ],
    "volkswagen_jetta": [
        (1980, 1984, "Volkswagen Jetta (Mk1)"),
        (1985, 1992, "Volkswagen Jetta (Mk2)"),
        (1993, 1998, "Volkswagen Jetta (Mk3)"),
        (1999, 2005, "Volkswagen Jetta (Mk4)"),
        (2006, 2010, "Volkswagen Jetta (Mk5)"),
        (2011, 2018, "Volkswagen Jetta (Mk6)"),
    ],
    "volkswagen_jetta_wagon": [
        (2002, 2005, "Volkswagen Jetta Wagon (Mk4)"),
        (2007, 2014, "Volkswagen Jetta SportWagen (Mk5)"),
    ],
    "volkswagen_karmannghia": [(1955, 1974, "Volkswagen Karmann Ghia (Type 14)")],
    "volkswagen_newbeetle": [
        (1998, 2010, "Volkswagen New Beetle (A4)"),
        (2011, 2019, "Volkswagen Beetle (A5)"),
    ],
    "volkswagen_passat": [
        (1973, 1980, "Volkswagen Passat (B1/B2)"),
        (1981, 1987, "Volkswagen Passat (B2)"),
        (1988, 1993, "Volkswagen Passat (B3)"),
        (1994, 1997, "Volkswagen Passat (B4)"),
        (1998, 2005, "Volkswagen Passat (B5)"),
        (2006, 2010, "Volkswagen Passat (B6)"),
        (2011, 2019, "Volkswagen Passat (B7)"),
    ],
    "volkswagen_passat_wagon": [
        (1994, 1997, "Volkswagen Passat Wagon (B4)"),
        (1998, 2005, "Volkswagen Passat Wagon (B5)"),
        (2006, 2010, "Volkswagen Passat Wagon (B6)"),
    ],
    "volkswagen_phaeton": [(2002, 2016, "Volkswagen Phaeton (1st Generation)")],
    "volkswagen_r32": [
        (2004, 2004, "Volkswagen R32 (Mk4)"),
        (2005, 2008, "Volkswagen R32 (Mk5)"),
    ],
    "volkswagen_rabbit": [
        (1974, 1984, "Volkswagen Rabbit (Mk1)"),
        (2006, 2009, "Volkswagen Rabbit (Mk5)"),
    ],
    "volkswagen_routan": [(2008, 2012, "Volkswagen Routan (1st Generation)")],
    "volkswagen_scirocco": [
        (1974, 1981, "Volkswagen Scirocco (Mk1)"),
        (1982, 1992, "Volkswagen Scirocco (Mk2)"),
    ],
    "volkswagen_squareback": [(1961, 1973, "Volkswagen Squareback (Type 3)")],
    "volkswagen_superbeetle": [(1971, 1975, "Volkswagen Super Beetle (Type 1)")],
    "volkswagen_tiguan": [
        (2007, 2017, "Volkswagen Tiguan (5N)"),
    ],
    "volkswagen_touareg": [
        (2002, 2010, "Volkswagen Touareg (7L)"),
        (2011, 2018, "Volkswagen Touareg (7P)"),
    ],
    "volkswagen_vanagon": [(1979, 1991, "Volkswagen Vanagon (T3)")],
    # ── VOLVO ─────────────────────────────────────────────────────────────────
    "volvo_142": [(1966, 1974, "Volvo 142 (140-Series)")],
    "volvo_145_wagon": [(1966, 1974, "Volvo 145 (140-Series)")],
    "volvo_164": [(1968, 1975, "Volvo 164 (140-Series)")],
    "volvo_240": [(1974, 1993, "Volvo 240 (200-Series)")],
    "volvo_240_wagon": [(1974, 1993, "Volvo 240 Wagon (200-Series)")],
    "volvo_242": [(1974, 1984, "Volvo 242 (200-Series)")],
    "volvo_244": [(1974, 1993, "Volvo 244 (200-Series)")],
    "volvo_245": [(1974, 1993, "Volvo 245 (200-Series)")],
    "volvo_540": [(1995, 2009, "Volvo 540 (Commercial Truck)")],
    "volvo_670": [(2003, 2014, "Volvo 670 (Commercial Truck)")],
    "volvo_740": [(1984, 1992, "Volvo 740 (700-Series)")],
    "volvo_740_wagon": [(1984, 1992, "Volvo 740 Wagon (700-Series)")],
    "volvo_760": [(1982, 1990, "Volvo 760 (700-Series)")],
    "volvo_760_wagon": [(1982, 1990, "Volvo 760 Wagon (700-Series)")],
    "volvo_780": [(2003, 2016, "Volvo 780 (Commercial Truck)")],
    "volvo_840": [(2003, 2014, "Volvo 840 (Commercial Truck)")],
    "volvo_850": [(1991, 1997, "Volvo 850 (P80)")],
    "volvo_850_wagon": [(1991, 1997, "Volvo 850 Wagon (P80)")],
    "volvo_940": [(1990, 1998, "Volvo 940 (900-Series)")],
    "volvo_940_wagon": [(1990, 1998, "Volvo 940 Wagon (900-Series)")],
    "volvo_960": [(1990, 1998, "Volvo 960 (900-Series)")],
    "volvo_960_wagon": [(1990, 1998, "Volvo 960 Wagon (900-Series)")],
    "volvo_c30": [(2006, 2013, "Volvo C30 (P1)")],
    "volvo_c40": [(2001, 2001, "Volvo C40 (1st Generation)")],
    "volvo_c70": [
        (1997, 2005, "Volvo C70 (1st Generation)"),
        (2006, 2013, "Volvo C70 (2nd Generation)"),
    ],
    "volvo_c70_convertible": [
        (1997, 2005, "Volvo C70 Convertible (1st Generation)"),
        (2006, 2013, "Volvo C70 Convertible (2nd Generation)"),
    ],
    "volvo_cx90": [(2003, 2014, "Volvo XC90 (1st Generation)")],   # typo for xc90
    "volvo_pv444": [(1944, 1958, "Volvo PV444")],
    "volvo_s40": [
        (1995, 2004, "Volvo S40 (1st Generation)"),
        (2005, 2012, "Volvo S40 (2nd Generation)"),
    ],
    "volvo_s60": [
        (2000, 2009, "Volvo S60 (1st Generation)"),
        (2010, 2018, "Volvo S60 (2nd Generation)"),
    ],
    "volvo_s70": [(1997, 2000, "Volvo S70 (P80)")],
    "volvo_s80": [
        (1998, 2006, "Volvo S80 (1st Generation)"),
        (2007, 2016, "Volvo S80 (2nd Generation)"),
    ],
    "volvo_s90": [(1996, 1998, "Volvo S90 (1st Generation)")],
    "volvo_v40": [
        (1995, 2004, "Volvo V40 (1st Generation)"),
        (2012, 2019, "Volvo V40 (2nd Generation)"),
    ],
    "volvo_v50": [(2004, 2012, "Volvo V50 (P1)")],
    "volvo_v70": [
        (1996, 2000, "Volvo V70 (1st Generation)"),
        (2001, 2007, "Volvo V70 (2nd Generation)"),
        (2008, 2016, "Volvo V70 (3rd Generation)"),
    ],
    "volvo_v90": [(1996, 1998, "Volvo V90 (1st Generation)")],
    "volvo_vnl": [(1996, 2024, "Volvo VNL (Commercial Truck)")],
    "volvo_xc60": [(2008, 2017, "Volvo XC60 (1st Generation)")],
    "volvo_xc70": [
        (1997, 2007, "Volvo XC70 (1st Generation)"),
        (2008, 2016, "Volvo XC70 (2nd Generation)"),
    ],
    "volvo_xc90": [(2002, 2014, "Volvo XC90 (1st Generation)")],
    # ── SAAB ──────────────────────────────────────────────────────────────────
    "saab_9-2": [(2005, 2006, "Saab 9-2X (1st Generation)")],
    "saab_9-3": [
        (1998, 2002, "Saab 9-3 (1st Generation)"),
        (2003, 2011, "Saab 9-3 (2nd Generation)"),
    ],
    "saab_9-3_convertible": [
        (1998, 2002, "Saab 9-3 Convertible (1st Generation)"),
        (2003, 2011, "Saab 9-3 Convertible (2nd Generation)"),
    ],
    "saab_9-5": [
        (1997, 2009, "Saab 9-5 (1st Generation)"),
        (2010, 2011, "Saab 9-5 (2nd Generation)"),
    ],
    "saab_9-6": [(1960, 1980, "Saab 96")],
    "saab_9-7": [(2005, 2009, "Saab 9-7X (1st Generation)")],
    "saab_900": [
        (1978, 1993, "Saab 900 (Classic)"),
        (1994, 1998, "Saab 900 (NG900/9-3)"),
    ],
    # ── MINI ──────────────────────────────────────────────────────────────────
    "mini_austin": [(1959, 2000, "Mini (Classic)")],
    "mini_cooper": [
        (2001, 2006, "MINI Cooper (R50/R53)"),
        (2007, 2013, "MINI Cooper (R56)"),
        (2014, 2019, "MINI Cooper (F56)"),
    ],
    "mini_cooper_countryman": [(2010, 2016, "MINI Cooper Countryman (R60)")],
    # ── ALFA ROMEO ────────────────────────────────────────────────────────────
    "alfa romeo_4c": [(2013, 2020, "Alfa Romeo 4C (1st Generation)")],
    "alfa romeo_alfetta_gt": [(1974, 1987, "Alfa Romeo Alfetta GT (1st Generation)")],
    "alfa romeo_spider": [
        (1966, 1982, "Alfa Romeo Spider (1st Generation)"),
        (1983, 1993, "Alfa Romeo Spider (3rd Generation)"),
    ],
    # ── ASTON MARTIN ──────────────────────────────────────────────────────────
    "aston martin_db9": [(2004, 2016, "Aston Martin DB9 (1st Generation)")],
    "aston martin_vantage": [(2005, 2018, "Aston Martin V8 Vantage (1st Generation)")],
    # ── BENTLEY ───────────────────────────────────────────────────────────────
    "bentley_arnage": [(1998, 2009, "Bentley Arnage (1st Generation)")],
    "bentley_brooklands": [(1992, 1998, "Bentley Brooklands (1st Generation)")],
    "bentley_continental": [
        (2003, 2011, "Bentley Continental GT (1st Generation)"),
        (2012, 2017, "Bentley Continental GT (2nd Generation)"),
    ],
    "bentley_turbo_r": [(1985, 1997, "Bentley Turbo R (1st Generation)")],
    # ── FIAT ──────────────────────────────────────────────────────────────────
    "fiat_doblo": [
        (2000, 2009, "Fiat Doblo (1st Generation)"),
        (2010, 2022, "Fiat Doblo (2nd Generation)"),
    ],
    "fiat_five hundred": [
        (1957, 1975, "Fiat 500 (Classic)"),
        (2007, 2019, "Fiat 500 (3rd Generation)"),
    ],
    "fiat_spider": [(1966, 1985, "Fiat 124 Spider (1st Generation)")],
    "fiat_x19": [(1972, 1989, "Fiat X1/9 (1st Generation)")],
    # ── JAGUAR ────────────────────────────────────────────────────────────────
    "jaguar_s-type": [
        (1963, 1968, "Jaguar S-Type (Classic)"),
        (1999, 2008, "Jaguar S-Type (X200)"),
    ],
    "jaguar_vandenplas": [
        (1979, 1992, "Jaguar XJ Vanden Plas (Series III/XJ40)"),
        (1993, 1997, "Jaguar XJ Vanden Plas (X300)"),
        (1998, 2003, "Jaguar XJ Vanden Plas (X308)"),
        (2004, 2009, "Jaguar XJ Vanden Plas (X350)"),
    ],
    "jaguar_x-type": [(2001, 2009, "Jaguar X-Type (X400)")],
    "jaguar_xf": [
        (2007, 2015, "Jaguar XF (X250)"),
        (2016, 2024, "Jaguar XF (X260)"),
    ],
    "jaguar_xj": [
        (1968, 1972, "Jaguar XJ (Series I)"),
        (1973, 1978, "Jaguar XJ (Series II)"),
        (1979, 1992, "Jaguar XJ (Series III/XJ40)"),
        (1993, 1997, "Jaguar XJ (X300)"),
        (1998, 2003, "Jaguar XJ (X308)"),
        (2004, 2009, "Jaguar XJ (X350)"),
        (2010, 2019, "Jaguar XJ (X351)"),
    ],
    "jaguar_xj_convertible": [(1979, 1992, "Jaguar XJ Convertible (Series III/XJ40)")],
    "jaguar_xk": [
        (1948, 1954, "Jaguar XK120"),
        (1955, 1957, "Jaguar XK140"),
        (1958, 1961, "Jaguar XK150"),
        (1962, 1975, "Jaguar E-Type (XKE)"),
        (1996, 2006, "Jaguar XK (X100)"),
        (2007, 2014, "Jaguar XK (X150)"),
    ],
    # ── LAMBORGHINI ───────────────────────────────────────────────────────────
    "lamborghini_gallardo": [(2003, 2013, "Lamborghini Gallardo (1st Generation)")],
    # ── LAND ROVER ────────────────────────────────────────────────────────────
    "landrover_defender": [(1983, 2016, "Land Rover Defender (1st Generation)")],
    "landrover_discovery": [
        (1989, 1998, "Land Rover Discovery (Series 1)"),
        (1999, 2004, "Land Rover Discovery (Series 2)"),
    ],
    "landrover_freelander": [
        (1997, 2006, "Land Rover Freelander (1st Generation)"),
        (2006, 2014, "Land Rover Freelander (2nd Generation)"),
    ],
    "landrover_lr2": [(2006, 2014, "Land Rover LR2 (Freelander 2)")],
    "landrover_lr3": [(2004, 2009, "Land Rover LR3 (Discovery 3)")],
    "landrover_lr4": [(2009, 2016, "Land Rover LR4 (Discovery 4)")],
    "landrover_rangerover": [
        (1970, 1995, "Land Rover Range Rover (Classic)"),
        (1994, 2002, "Land Rover Range Rover (P38)"),
        (2002, 2012, "Land Rover Range Rover (L322)"),
        (2013, 2022, "Land Rover Range Rover (L405)"),
    ],
    # ── LOTUS ─────────────────────────────────────────────────────────────────
    "lotus_elan": [(1989, 1995, "Lotus Elan (M100)")],
    "lotus_elise": [
        (1996, 2001, "Lotus Elise (Series 1)"),
        (2001, 2010, "Lotus Elise (Series 2)"),
        (2010, 2021, "Lotus Elise (Series 3)"),
    ],
    "lotus_esprit": [
        (1976, 1987, "Lotus Esprit (Series 1-3)"),
        (1987, 1993, "Lotus Esprit (Series 4)"),
        (1993, 2004, "Lotus Esprit (V8)"),
    ],
    "lotus_evora": [(2009, 2021, "Lotus Evora (1st Generation)")],
    # ── MASERATI ──────────────────────────────────────────────────────────────
    "maserati_biturbo": [(1981, 1994, "Maserati Biturbo (1st Generation)")],
    "maserati_ghibli": [(2013, 2023, "Maserati Ghibli (M157)")],
    "maserati_gransport": [(2002, 2007, "Maserati GranSport (M138)")],
    "maserati_granturismo": [(2007, 2019, "Maserati GranTurismo (M145)")],
    "maserati_quattroporte": [
        (1963, 1969, "Maserati Quattroporte (1st Generation)"),
        (1994, 2001, "Maserati Quattroporte (4th Generation)"),
        (2003, 2012, "Maserati Quattroporte (M139)"),
    ],
    "maserati_spyder": [(2001, 2007, "Maserati Spyder (M138)")],
    "maserati_tc": [(1989, 1991, "Maserati TC by Chrysler")],
    # ── ROLLS-ROYCE ───────────────────────────────────────────────────────────
    "rolls royce_corniche": [(1971, 1996, "Rolls-Royce Corniche (1st Generation)")],
    "rolls royce_silvershadow": [
        (1965, 1977, "Rolls-Royce Silver Shadow (1st Generation)"),
        (1977, 1980, "Rolls-Royce Silver Shadow (2nd Generation)"),
    ],
    "rolls royce_silverspur": [(1980, 1999, "Rolls-Royce Silver Spur (1st Generation)")],
    # ── FERRARI ───────────────────────────────────────────────────────────────
    "ferrari_360 modena": [(1999, 2005, "Ferrari 360 Modena")],
    "ferrari_daytona": [(1968, 1973, "Ferrari 365 GTB/4 Daytona")],
    "ferrari_dino": [(1968, 1974, "Ferrari Dino 246")],
    "ferrari_f430": [(2004, 2009, "Ferrari F430")],
    "ferrari_gtm": [(2008, 2008, "Ferrari GTM")],
    "ferrari_testarossa": [(1984, 1996, "Ferrari Testarossa")],
    # ── OPEL ──────────────────────────────────────────────────────────────────
    "opel_astra": [
        (1991, 1998, "Opel Astra (F)"),
        (1998, 2004, "Opel Astra (G)"),
        (2004, 2009, "Opel Astra (H)"),
        (2010, 2015, "Opel Astra (J)"),
    ],
    "opel_gt": [(1968, 1973, "Opel GT (1st Generation)")],
    "opel_kadett": [
        (1962, 1965, "Opel Kadett (A)"),
        (1965, 1973, "Opel Kadett (B/C)"),
    ],
    "opel_vivaro": [
        (2001, 2014, "Opel Vivaro (A)"),
        (2014, 2019, "Opel Vivaro (B)"),
    ],
    # ── HOLDEN ────────────────────────────────────────────────────────────────
    "holden_commodore": [
        (2004, 2006, "Holden Commodore (VZ)"),
        (2007, 2013, "Holden Commodore (VE)"),
    ],
    # ── SMART ─────────────────────────────────────────────────────────────────
    "smart_fortwo": [
        (1998, 2007, "Smart Fortwo (W450)"),
        (2007, 2014, "Smart Fortwo (W451)"),
        (2015, 2019, "Smart Fortwo (W453)"),
    ],
    # ── CITROËN ───────────────────────────────────────────────────────────────
    "citroen_ds5": [(2011, 2018, "Citroen DS5 (1st Generation)")],
    "citroen_mehari": [(1968, 1988, "Citroen Mehari (1st Generation)")],
    # ── PEUGEOT ───────────────────────────────────────────────────────────────
    "peugeot_3008": [
        (2009, 2016, "Peugeot 3008 (1st Generation)"),
        (2016, 2023, "Peugeot 3008 (2nd Generation)"),
    ],
    "peugeot_407_wagon": [(2004, 2011, "Peugeot 407 SW (1st Generation)")],
}

# ─────────────────────────────────────────────────────────────────────────────
# JAPANESE / KOREAN MAP  (to be filled by agent)
# ─────────────────────────────────────────────────────────────────────────────
JAPANESE_MAP = {
    # ── ACURA ─────────────────────────────────────────────────────────────────
    "acura_cl": [
        (1997, 1999, "Acura CL (1st Generation)"),
        (2001, 2003, "Acura CL (2nd Generation)"),
    ],
    "acura_el": [
        (1997, 2000, "Acura EL (1st Generation)"),
        (2001, 2005, "Acura EL (2nd Generation)"),
    ],
    "acura_ilx":       [(2013, 2022, "Acura ILX (1st Generation)")],
    "acura_integra": [
        (1986, 1989, "Acura Integra (DA)"),
        (1990, 1993, "Acura Integra (DB)"),
        (1994, 2001, "Acura Integra (DC2/DC4)"),
    ],
    "acura_legend": [
        (1987, 1990, "Acura Legend (1st Generation)"),
        (1991, 1996, "Acura Legend (2nd Generation)"),
        (2001, 2004, "Acura RL (KA9)"),
    ],
    "acura_mdx": [
        (1996, 1996, "Acura SLX (1st Generation)"),
        (2001, 2006, "Acura MDX (1st Generation YD1)"),
        (2007, 2013, "Acura MDX (2nd Generation YD2)"),
        (2014, 2020, "Acura MDX (3rd Generation YD3)"),
    ],
    "acura_nsx":       [(1991, 2005, "Acura NSX (NA1/NA2)")],
    "acura_rdx": [
        (2007, 2012, "Acura RDX (1st Generation TB1)"),
        (2013, 2018, "Acura RDX (2nd Generation TB3)"),
    ],
    "acura_rl": [
        (1996, 2004, "Acura RL (1st Generation KA9)"),
        (2005, 2012, "Acura RL (2nd Generation KB1)"),
    ],
    "acura_rsx":       [(2002, 2006, "Acura RSX (DC5)")],
    "acura_slx":       [(1996, 1999, "Acura SLX (1st Generation)")],
    "acura_tl": [
        (1995, 1998, "Acura TL (1st Generation UA1/UA2)"),
        (1999, 2003, "Acura TL (2nd Generation UA5)"),
        (2004, 2008, "Acura TL (3rd Generation UA6/UA7)"),
        (2009, 2014, "Acura TL (4th Generation UA8/UA9)"),
    ],
    "acura_tlx":       [(2015, 2020, "Acura TLX (1st Generation UB1)")],
    "acura_tsx": [
        (2004, 2008, "Acura TSX (1st Generation CL9)"),
        (2009, 2014, "Acura TSX (2nd Generation CU2)"),
    ],
    "acura_tsx_wagon": [(2011, 2014, "Acura TSX Wagon (2nd Generation)")],
    "acura_vigor":     [(1992, 1994, "Acura Vigor (CC2)")],
    "acura_zdx":       [(2010, 2013, "Acura ZDX (1st Generation)")],
    # ── HONDA ─────────────────────────────────────────────────────────────────
    "honda_accord": [
        (1976, 1981, "Honda Accord (1st Generation)"),
        (1982, 1985, "Honda Accord (2nd Generation)"),
        (1986, 1989, "Honda Accord (3rd Generation)"),
        (1990, 1993, "Honda Accord (4th Generation CB)"),
        (1994, 1997, "Honda Accord (5th Generation CD)"),
        (1998, 2002, "Honda Accord (6th Generation CG/CF)"),
        (2003, 2007, "Honda Accord (7th Generation CM)"),
        (2008, 2012, "Honda Accord (8th Generation CP/CU)"),
    ],
    "honda_accord_2 door": [
        (1976, 1981, "Honda Accord (1st Generation)"),
        (1982, 1985, "Honda Accord (2nd Generation)"),
        (1986, 1989, "Honda Accord (3rd Generation)"),
        (1990, 1993, "Honda Accord Coupe (4th Generation CB)"),
        (1994, 1997, "Honda Accord Coupe (5th Generation CD)"),
        (1998, 2002, "Honda Accord Coupe (6th Generation CG)"),
        (2003, 2007, "Honda Accord Coupe (7th Generation CM)"),
        (2008, 2012, "Honda Accord Coupe (8th Generation CP)"),
    ],
    "honda_accord_wagon": [
        (1990, 1993, "Honda Accord Wagon (4th Generation)"),
        (1994, 1997, "Honda Accord Wagon (5th Generation)"),
    ],
    "honda_beat":      [(1991, 1996, "Honda Beat (PP1)")],
    "honda_city": [
        (1981, 1994, "Honda City (1st/2nd Generation)"),
        (1996, 2002, "Honda City (3rd Generation)"),
    ],
    "honda_civic": [
        (1973, 1979, "Honda Civic (1st Generation)"),
        (1980, 1983, "Honda Civic (2nd Generation)"),
        (1984, 1987, "Honda Civic (3rd Generation)"),
        (1988, 1991, "Honda Civic (4th Generation EF)"),
        (1992, 1995, "Honda Civic (5th Generation EG)"),
        (1996, 2000, "Honda Civic (6th Generation EK)"),
        (2001, 2005, "Honda Civic (7th Generation EP/ES)"),
        (2006, 2011, "Honda Civic (8th Generation FD)"),
        (2012, 2015, "Honda Civic (9th Generation FB)"),
    ],
    "honda_civic_coupe": [
        (1992, 1995, "Honda Civic Coupe (5th Generation EJ)"),
        (1996, 2000, "Honda Civic Coupe (6th Generation EJ)"),
        (2001, 2005, "Honda Civic Coupe (7th Generation ES)"),
        (2006, 2011, "Honda Civic Coupe (8th Generation FG)"),
        (2012, 2015, "Honda Civic Coupe (9th Generation FB)"),
    ],
    "honda_civic_hatchback": [
        (1988, 1991, "Honda Civic Hatchback (4th Generation EF)"),
        (1992, 1995, "Honda Civic Hatchback (5th Generation EG)"),
        (1996, 2000, "Honda Civic Hatchback (6th Generation EK)"),
        (2002, 2005, "Honda Civic Hatchback (7th Generation EU)"),
    ],
    "honda_cr-v": [
        (1997, 2001, "Honda CR-V (1st Generation RD)"),
        (2002, 2006, "Honda CR-V (2nd Generation RD7)"),
        (2007, 2011, "Honda CR-V (3rd Generation RE)"),
        (2012, 2016, "Honda CR-V (4th Generation RM)"),
    ],
    "honda_cr-z":      [(2011, 2016, "Honda CR-Z (ZF1/ZF2)")],
    "honda_crosstour": [(2010, 2015, "Honda Crosstour (TF)")],
    "honda_crx": [
        (1984, 1987, "Honda CRX (1st Generation AF)"),
        (1988, 1991, "Honda CRX (2nd Generation EF)"),
    ],
    "honda_delsol":    [(1992, 1997, "Honda Del Sol (EG2)")],
    "honda_element":   [(2003, 2011, "Honda Element (YH2)")],
    "honda_fit": [
        (2007, 2008, "Honda Fit (1st Generation GD)"),
        (2009, 2014, "Honda Fit (2nd Generation GE)"),
    ],
    "honda_hr-v":      [(2015, 2022, "Honda HR-V (2nd Generation RU)")],
    "honda_insight": [
        (2000, 2006, "Honda Insight (1st Generation ZE1)"),
        (2010, 2014, "Honda Insight (2nd Generation ZE2)"),
    ],
    "honda_jazz": [
        (2002, 2008, "Honda Jazz (1st Generation GD)"),
        (2008, 2015, "Honda Jazz (2nd Generation GE)"),
    ],
    "honda_odyssey": [
        (1995, 1998, "Honda Odyssey (1st Generation RA1)"),
        (1999, 2004, "Honda Odyssey (2nd Generation RL1)"),
        (2005, 2010, "Honda Odyssey (3rd Generation RL3)"),
        (2011, 2017, "Honda Odyssey (4th Generation RL5)"),
    ],
    "honda_passport": [
        (1994, 2002, "Honda Passport (1st Generation)"),
        (2019, 2022, "Honda Passport (2nd Generation)"),
    ],
    "honda_pilot": [
        (2003, 2008, "Honda Pilot (1st Generation YF1)"),
        (2009, 2015, "Honda Pilot (2nd Generation YF2)"),
    ],
    "honda_prelude": [
        (1979, 1982, "Honda Prelude (1st Generation SN)"),
        (1983, 1987, "Honda Prelude (2nd Generation AB)"),
        (1988, 1991, "Honda Prelude (3rd Generation BA)"),
        (1992, 1996, "Honda Prelude (4th Generation BB)"),
        (1997, 2001, "Honda Prelude (5th Generation BB6)"),
    ],
    "honda_ridgeline": [(2006, 2014, "Honda Ridgeline (1st Generation)")],
    "honda_s2000":     [(2000, 2009, "Honda S2000 (AP1/AP2)")],
    # ── HYUNDAI ───────────────────────────────────────────────────────────────
    "hyundai_accent": [
        (1995, 1999, "Hyundai Accent (1st Generation X3)"),
        (2000, 2005, "Hyundai Accent (2nd Generation LC)"),
        (2006, 2011, "Hyundai Accent (3rd Generation MC)"),
        (2012, 2017, "Hyundai Accent (4th Generation RB)"),
    ],
    "hyundai_azera": [
        (2006, 2011, "Hyundai Azera (1st Generation TG)"),
        (2012, 2017, "Hyundai Azera (2nd Generation HG)"),
    ],
    "hyundai_elantra": [
        (1991, 1995, "Hyundai Elantra (1st Generation J1)"),
        (1996, 2000, "Hyundai Elantra (2nd Generation J2)"),
        (2001, 2006, "Hyundai Elantra (3rd Generation XD)"),
        (2007, 2010, "Hyundai Elantra (4th Generation HD)"),
        (2011, 2016, "Hyundai Elantra (5th Generation MD)"),
    ],
    "hyundai_elantra_wagon": [(1996, 2000, "Hyundai Elantra Wagon (2nd Generation)")],
    "hyundai_entourage":     [(2007, 2009, "Hyundai Entourage (1st Generation)")],
    "hyundai_equus":         [(2009, 2016, "Hyundai Equus (VI)")],
    "hyundai_excel": [
        (1985, 1989, "Hyundai Excel (1st Generation X1)"),
        (1990, 1994, "Hyundai Excel (2nd Generation X2)"),
    ],
    "hyundai_genesis": [
        (2009, 2014, "Hyundai Genesis (1st Generation BH)"),
        (2015, 2016, "Hyundai Genesis (2nd Generation DH)"),
    ],
    "hyundai_genesis_coupe": [
        (2009, 2012, "Hyundai Genesis Coupe (1st Generation BK)"),
        (2013, 2016, "Hyundai Genesis Coupe (2nd Generation BK)"),
    ],
    "hyundai_santafe": [
        (2001, 2006, "Hyundai Santa Fe (1st Generation SM)"),
        (2007, 2012, "Hyundai Santa Fe (2nd Generation CM)"),
        (2013, 2018, "Hyundai Santa Fe (3rd Generation DM)"),
    ],
    "hyundai_sonata": [
        (1989, 1993, "Hyundai Sonata (2nd Generation Y2)"),
        (1994, 1998, "Hyundai Sonata (3rd Generation Y3)"),
        (1999, 2004, "Hyundai Sonata (4th Generation EF)"),
        (2005, 2010, "Hyundai Sonata (5th Generation NF)"),
        (2011, 2014, "Hyundai Sonata (6th Generation YF)"),
    ],
    "hyundai_tiburon": [
        (1996, 2001, "Hyundai Tiburon (1st Generation RD)"),
        (2003, 2008, "Hyundai Tiburon (2nd Generation GK)"),
    ],
    "hyundai_tucson": [
        (2005, 2009, "Hyundai Tucson (1st Generation JM)"),
        (2010, 2015, "Hyundai Tucson (2nd Generation LM)"),
    ],
    "hyundai_veloster":  [(2012, 2017, "Hyundai Veloster (1st Generation FS)")],
    "hyundai_veracruz":  [(2007, 2012, "Hyundai Veracruz (ix55)")],
    "hyundai_volester":  [(2012, 2017, "Hyundai Veloster (1st Generation FS)")],
    "hyundai_xg300":     [(2001, 2001, "Hyundai XG300 (1st Generation)")],
    "hyundai_xg350":     [(2002, 2005, "Hyundai XG350 (1st Generation)")],
    # ── INFINITI ──────────────────────────────────────────────────────────────
    "infiniti_fx35": [
        (2003, 2008, "Infiniti FX (S50)"),
        (2009, 2013, "Infiniti FX (S51)"),
    ],
    "infiniti_fx45":  [(2003, 2008, "Infiniti FX (S50)")],
    "infiniti_fx50s": [(2009, 2013, "Infiniti FX (S51)")],
    "infiniti_g20": [
        (1990, 1996, "Infiniti G20 (1st Generation P10)"),
        (2000, 2002, "Infiniti G20 (2nd Generation P11)"),
    ],
    "infiniti_g25":      [(2011, 2012, "Infiniti G25 (V36)")],
    "infiniti_g35": [
        (2003, 2006, "Infiniti G35 (V35)"),
        (2007, 2008, "Infiniti G35 (V36)"),
    ],
    "infiniti_g35_coupe": [(2003, 2007, "Infiniti G35 Coupe (V35)")],
    "infiniti_g37":       [(2008, 2013, "Infiniti G37 (V36)")],
    "infiniti_i30": [
        (1996, 1999, "Infiniti I30 (1st Generation)"),
        (2000, 2001, "Infiniti I30 (2nd Generation)"),
    ],
    "infiniti_i35": [(2002, 2004, "Infiniti I35 (2nd Generation)")],
    "infiniti_j30": [(1993, 1997, "Infiniti J30 (Y32)")],
    "infiniti_m30": [(1990, 1992, "Infiniti M30 (1st Generation)")],
    "infiniti_m35": [(2006, 2010, "Infiniti M35 (Y50)")],
    "infiniti_m45": [
        (2003, 2004, "Infiniti M45 (Y34)"),
        (2006, 2010, "Infiniti M45 (Y50)"),
    ],
    "infiniti_q45": [
        (1990, 1996, "Infiniti Q45 (1st Generation G50)"),
        (1997, 2001, "Infiniti Q45 (2nd Generation F50)"),
        (2002, 2006, "Infiniti Q45 (3rd Generation F50)"),
    ],
    "infiniti_q50":  [(2014, 2022, "Infiniti Q50 (V37)")],
    "infiniti_qx30": [(2017, 2019, "Infiniti QX30 (H15)")],
    "infiniti_qx4":  [(1997, 2003, "Infiniti QX4 (1st Generation)")],
    "infiniti_qx50": [(2014, 2019, "Infiniti QX50 (J50)")],
    "infiniti_qx56": [
        (2004, 2010, "Infiniti QX56 (1st Generation Z62)"),
        (2011, 2013, "Infiniti QX56 (2nd Generation Z62)"),
    ],
    # ── ISUZU ─────────────────────────────────────────────────────────────────
    "isuzu_amigo": [
        (1989, 1994, "Isuzu Amigo (1st Generation)"),
        (1998, 2000, "Isuzu Amigo (2nd Generation)"),
    ],
    "isuzu_ascender":  [(2003, 2008, "Isuzu Ascender (1st Generation)")],
    "isuzu_axiom":     [(2002, 2004, "Isuzu Axiom (1st Generation)")],
    "isuzu_hombre":    [(1996, 2000, "Isuzu Hombre (1st Generation)")],
    "isuzu_npr":       [(1984, 2024, "Isuzu N-Series (NPR)")],
    "isuzu_nqr":       [(1999, 2024, "Isuzu N-Series (NQR)")],
    "isuzu_pickup": [
        (1981, 1990, "Isuzu Pickup (1st Generation)"),
        (1991, 1996, "Isuzu Pickup (2nd Generation)"),
    ],
    "isuzu_rodeo": [
        (1991, 1997, "Isuzu Rodeo (1st Generation)"),
        (1998, 2004, "Isuzu Rodeo (2nd Generation)"),
    ],
    "isuzu_trooper": [
        (1984, 1991, "Isuzu Trooper (1st Generation)"),
        (1992, 2002, "Isuzu Trooper (2nd Generation)"),
    ],
    "isuzu_vehicross": [(1999, 2001, "Isuzu VehiCROSS (1st Generation)")],
    # ── KIA ───────────────────────────────────────────────────────────────────
    "kia_amanti":   [(2004, 2009, "Kia Amanti (1st Generation)")],
    "kia_cadenza":  [(2014, 2016, "Kia Cadenza (1st Generation)")],
    "kia_ceed":     [(2007, 2012, "Kia Ceed (1st Generation)")],
    "kia_forte": [
        (2010, 2013, "Kia Forte (1st Generation TD)"),
        (2014, 2018, "Kia Forte (2nd Generation YD)"),
    ],
    "kia_magentis": [
        (2001, 2005, "Kia Magentis (1st Generation GD)"),
        (2006, 2010, "Kia Magentis (2nd Generation MG)"),
    ],
    "kia_optima": [
        (2001, 2005, "Kia Optima (1st Generation GD)"),
        (2006, 2010, "Kia Optima (2nd Generation MG)"),
        (2011, 2015, "Kia Optima (3rd Generation TF)"),
    ],
    "kia_rio": [
        (2001, 2005, "Kia Rio (1st Generation DC)"),
        (2006, 2011, "Kia Rio (2nd Generation JB)"),
        (2012, 2017, "Kia Rio (3rd Generation UB)"),
    ],
    "kia_rio_wagon": [(2001, 2005, "Kia Rio Wagon (1st Generation)")],
    "kia_rondo":     [(2007, 2012, "Kia Rondo (1st Generation UN)")],
    "kia_sedona": [
        (2002, 2005, "Kia Sedona (1st Generation GQ)"),
        (2006, 2014, "Kia Sedona (2nd Generation VQ)"),
    ],
    "kia_sephia": [
        (1992, 1997, "Kia Sephia (1st Generation FA)"),
        (1998, 2003, "Kia Sephia (2nd Generation FA)"),
    ],
    "kia_sorento": [
        (2003, 2009, "Kia Sorento (1st Generation BL)"),
        (2010, 2015, "Kia Sorento (2nd Generation XM)"),
    ],
    "kia_soul": [
        (2010, 2013, "Kia Soul (1st Generation AM)"),
        (2014, 2019, "Kia Soul (2nd Generation PS)"),
    ],
    "kia_spectra": [
        (2000, 2004, "Kia Spectra (1st Generation SD)"),
        (2005, 2009, "Kia Spectra (2nd Generation LD)"),
    ],
    "kia_spectra5":  [(2005, 2009, "Kia Spectra5 (LD)")],
    "kia_sportage": [
        (1993, 2002, "Kia Sportage (1st Generation JA)"),
        (2005, 2010, "Kia Sportage (2nd Generation KM)"),
        (2011, 2016, "Kia Sportage (3rd Generation SL)"),
    ],
    # ── LEXUS ─────────────────────────────────────────────────────────────────
    "lexus_ct":      [(2011, 2017, "Lexus CT (ZWA10)")],
    "lexus_es300": [
        (1992, 1996, "Lexus ES 300 (XV10)"),
        (1997, 2001, "Lexus ES 300 (XV20)"),
        (2002, 2003, "Lexus ES 300 (XV30)"),
    ],
    "lexus_es330":   [(2004, 2006, "Lexus ES 330 (XV30)")],
    "lexus_es350": [
        (2007, 2012, "Lexus ES 350 (XV40)"),
        (2013, 2018, "Lexus ES 350 (XV60)"),
    ],
    "lexus_gs300": [
        (1993, 1997, "Lexus GS 300 (S140)"),
        (1998, 2005, "Lexus GS 300 (S160)"),
    ],
    "lexus_gs350": [
        (2007, 2011, "Lexus GS 350 (S190)"),
        (2012, 2020, "Lexus GS 350 (L10)"),
    ],
    "lexus_gs400":   [(1998, 2005, "Lexus GS 400 (S160)")],
    "lexus_gs430":   [(2001, 2007, "Lexus GS 430 (S160)")],
    "lexus_gs450":   [(2007, 2011, "Lexus GS 450h (S190)")],
    "lexus_gs460":   [(2008, 2011, "Lexus GS 460 (S190)")],
    "lexus_gx370":   [(2003, 2009, "Lexus GX 470 (J120)")],   # mislabeled
    "lexus_gx450":   [(2003, 2009, "Lexus GX 470 (J120)")],   # mislabeled
    "lexus_gx460":   [(2010, 2023, "Lexus GX 460 (J150)")],
    "lexus_gx470":   [(2003, 2009, "Lexus GX 470 (J120)")],
    "lexus_hs250h":  [(2010, 2012, "Lexus HS 250h (ANF10)")],
    "lexus_is200":   [(1999, 2005, "Lexus IS 200 (XE10)")],
    "lexus_is250": [
        (2006, 2013, "Lexus IS 250 (XE20)"),
        (2014, 2020, "Lexus IS 250 (XE30)"),
    ],
    "lexus_is300": [
        (2001, 2005, "Lexus IS 300 (XE10)"),
        (2016, 2020, "Lexus IS 300 (XE30)"),
    ],
    "lexus_is350": [
        (2006, 2013, "Lexus IS 350 (XE20)"),
        (2014, 2020, "Lexus IS 350 (XE30)"),
    ],
    "lexus_ls400": [
        (1990, 1994, "Lexus LS 400 (Z30)"),
        (1995, 2000, "Lexus LS 400 (Z40)"),
    ],
    "lexus_ls430":   [(2001, 2006, "Lexus LS 430 (Z40)")],
    "lexus_ls460":   [(2007, 2012, "Lexus LS 460 (Z50)")],
    "lexus_lx450":   [(1996, 1997, "Lexus LX 450 (J80)")],
    "lexus_lx470":   [(1998, 2007, "Lexus LX 470 (J100)")],
    "lexus_lx570":   [(2008, 2021, "Lexus LX 570 (J200)")],
    "lexus_nx200t":  [(2015, 2021, "Lexus NX (AZ10)")],
    "lexus_rc350":   [(2015, 2023, "Lexus RC 350 (XC10)")],
    "lexus_rx300":   [(1999, 2003, "Lexus RX 300 (XU10)")],
    "lexus_rx330":   [(2004, 2006, "Lexus RX 330 (XU30)")],
    "lexus_rx350": [
        (2007, 2009, "Lexus RX 350 (XU30)"),
        (2010, 2015, "Lexus RX 350 (AL10)"),
    ],
    "lexus_rx400h":  [(2006, 2008, "Lexus RX 400h (XU30)")],
    "lexus_sc300":   [(1992, 2000, "Lexus SC 300 (Z30)")],
    "lexus_sc400":   [(1992, 2000, "Lexus SC 400 (Z30)")],
    "lexus_sc430":   [(2002, 2010, "Lexus SC 430 (Z40)")],
    # ── MAZDA ─────────────────────────────────────────────────────────────────
    "mazda_2":        [(2011, 2014, "Mazda2 (2nd Generation DE)")],
    "mazda_3": [
        (2004, 2009, "Mazda3 (1st Generation BK)"),
        (2010, 2013, "Mazda3 (2nd Generation BL)"),
    ],
    "mazda_323": [
        (1977, 1989, "Mazda 323/Familia (1st-3rd Generation)"),
        (1990, 1994, "Mazda 323 (4th Generation BG)"),
    ],
    "mazda_3_hatchback": [
        (2004, 2009, "Mazda3 Hatchback (1st Generation BK)"),
        (2010, 2013, "Mazda3 Hatchback (2nd Generation BL)"),
    ],
    "mazda_5": [
        (2006, 2010, "Mazda5 (1st Generation CR)"),
        (2011, 2017, "Mazda5 (2nd Generation CW)"),
    ],
    "mazda_6": [
        (2003, 2007, "Mazda6 (1st Generation GG/GY)"),
        (2009, 2013, "Mazda6 (2nd Generation GH)"),
    ],
    "mazda_626": [
        (1979, 1982, "Mazda 626 (1st Generation CB)"),
        (1983, 1987, "Mazda 626 (2nd Generation GC)"),
        (1988, 1992, "Mazda 626 (3rd Generation GD)"),
        (1993, 1997, "Mazda 626 (4th Generation GE)"),
        (1998, 2002, "Mazda 626 (5th Generation GF)"),
    ],
    "mazda_6_wagon":  [(2003, 2007, "Mazda6 Wagon (1st Generation GY)")],
    "mazda_929": [
        (1988, 1991, "Mazda 929 (HC)"),
        (1992, 1995, "Mazda 929 (HD)"),
    ],
    "mazda_b2000":    [(1981, 1985, "Mazda B-Series (1st Generation)")],
    "mazda_b2200":    [(1986, 1993, "Mazda B-Series (2nd Generation)")],
    "mazda_b2300": [
        (1994, 1997, "Mazda B-Series (3rd Generation)"),
        (1998, 2003, "Mazda B-Series (4th Generation)"),
    ],
    "mazda_b2500":    [(1998, 2001, "Mazda B-Series (4th Generation)")],
    "mazda_b2600":    [(1986, 1993, "Mazda B-Series (2nd Generation)")],
    "mazda_b3000": [
        (1994, 1997, "Mazda B-Series (3rd Generation)"),
        (1998, 2010, "Mazda B-Series (4th Generation)"),
    ],
    "mazda_b4000":    [(1994, 2010, "Mazda B-Series (4th Generation)")],
    "mazda_cx5":      [(2013, 2016, "Mazda CX-5 (1st Generation KE)")],
    "mazda_cx7":      [(2007, 2012, "Mazda CX-7 (1st Generation ER)")],
    "mazda_cx9":      [(2007, 2015, "Mazda CX-9 (1st Generation TB)")],
    "mazda_millenia": [(1994, 2002, "Mazda Millenia (1st Generation TA)")],
    "mazda_mpv": [
        (1988, 1999, "Mazda MPV (1st Generation LV)"),
        (2000, 2006, "Mazda MPV (2nd Generation LW)"),
    ],
    "mazda_mx3":      [(1992, 1997, "Mazda MX-3 (1st Generation EC)")],
    "mazda_mx5_miata": [
        (1990, 1997, "Mazda MX-5 Miata (1st Generation NA)"),
        (1998, 2005, "Mazda MX-5 Miata (2nd Generation NB)"),
        (2006, 2015, "Mazda MX-5 Miata (3rd Generation NC)"),
    ],
    "mazda_mx6": [
        (1988, 1992, "Mazda MX-6 (1st Generation GD)"),
        (1993, 1997, "Mazda MX-6 (2nd Generation GE)"),
    ],
    "mazda_navajo":   [(1991, 1994, "Mazda Navajo (1st Generation)")],
    "mazda_protege": [
        (1990, 1994, "Mazda Protege (1st Generation BG)"),
        (1995, 1998, "Mazda Protege (2nd Generation BH)"),
        (1999, 2003, "Mazda Protege (3rd Generation BJ)"),
    ],
    "mazda_rx7": [
        (1979, 1985, "Mazda RX-7 (1st Generation SA/FB)"),
        (1986, 1991, "Mazda RX-7 (2nd Generation FC)"),
        (1992, 2002, "Mazda RX-7 (3rd Generation FD)"),
    ],
    "mazda_rx8":      [(2003, 2012, "Mazda RX-8 (SE3P)")],
    "mazda_speed3": [
        (2007, 2009, "Mazdaspeed3 (1st Generation BK)"),
        (2010, 2013, "Mazdaspeed3 (2nd Generation BL)"),
    ],
    "mazda_speed6":   [(2006, 2007, "Mazdaspeed6 (1st Generation GG)")],
    "mazda_tribute": [
        (2001, 2006, "Mazda Tribute (1st Generation EP)"),
        (2008, 2011, "Mazda Tribute (2nd Generation GP)"),
    ],
    # ── MITSUBISHI ────────────────────────────────────────────────────────────
    "mitsubishi_3000gt": [
        (1990, 1993, "Mitsubishi 3000GT (1st Generation Z16A)"),
        (1994, 1999, "Mitsubishi 3000GT (2nd Generation Z16A)"),
    ],
    "mitsubishi_chariot": [
        (1984, 1991, "Mitsubishi Chariot (1st Generation)"),
        (1991, 2003, "Mitsubishi Chariot (2nd Generation)"),
    ],
    "mitsubishi_colt":    [(1970, 1977, "Mitsubishi Colt (1st Generation)")],
    "mitsubishi_delica": [
        (1968, 1986, "Mitsubishi Delica (1st/2nd Generation)"),
        (1986, 1994, "Mitsubishi Delica (3rd Generation)"),
        (1994, 2007, "Mitsubishi Delica (4th Generation)"),
    ],
    "mitsubishi_diamante": [
        (1991, 1996, "Mitsubishi Diamante (1st Generation F11A)"),
        (1997, 2004, "Mitsubishi Diamante (2nd Generation F36A)"),
    ],
    "mitsubishi_eclipse": [
        (1989, 1994, "Mitsubishi Eclipse (1st Generation D22A)"),
        (1995, 1999, "Mitsubishi Eclipse (2nd Generation D32A)"),
        (2000, 2005, "Mitsubishi Eclipse (3rd Generation D52A)"),
        (2006, 2012, "Mitsubishi Eclipse (4th Generation DK)"),
    ],
    "mitsubishi_eclipse_convertible": [
        (1995, 1999, "Mitsubishi Eclipse Spyder (2nd Generation D32A)"),
        (2000, 2005, "Mitsubishi Eclipse Spyder (3rd Generation D52A)"),
        (2006, 2012, "Mitsubishi Eclipse Spyder (4th Generation DK)"),
    ],
    "mitsubishi_endeavor": [(2004, 2011, "Mitsubishi Endeavor (1st Generation)")],
    "mitsubishi_fuso":     [(1935, 2024, "Mitsubishi Fuso (Commercial Truck)")],
    "mitsubishi_galant": [
        (1969, 1973, "Mitsubishi Galant (1st Generation)"),
        (1994, 1998, "Mitsubishi Galant (7th Generation EA)"),
        (1999, 2003, "Mitsubishi Galant (8th Generation EA)"),
        (2004, 2012, "Mitsubishi Galant (9th Generation DJ)"),
    ],
    "mitsubishi_lancer": [
        (1992, 1995, "Mitsubishi Lancer (5th Generation CB)"),
        (1996, 2003, "Mitsubishi Lancer (6th Generation CK)"),
        (2004, 2006, "Mitsubishi Lancer (7th Generation CS)"),
        (2007, 2017, "Mitsubishi Lancer (8th Generation CY)"),
    ],
    "mitsubishi_mighty max": [
        (1979, 1986, "Mitsubishi Mighty Max (1st Generation L025)"),
        (1987, 1996, "Mitsubishi Mighty Max (2nd Generation L200)"),
    ],
    "mitsubishi_mirage": [
        (1978, 1983, "Mitsubishi Mirage (1st Generation A151A)"),
        (1984, 1987, "Mitsubishi Mirage (2nd Generation A170A)"),
        (1988, 1992, "Mitsubishi Mirage (3rd Generation A170A)"),
        (2014, 2020, "Mitsubishi Mirage (5th Generation A05A)"),
    ],
    "mitsubishi_montero": [
        (1982, 1991, "Mitsubishi Montero (1st Generation L040)"),
        (1992, 1999, "Mitsubishi Montero (2nd Generation V20-40)"),
        (2000, 2006, "Mitsubishi Montero (3rd Generation V60-80)"),
    ],
    "mitsubishi_outlander": [
        (2003, 2006, "Mitsubishi Outlander (1st Generation CU2W)"),
        (2007, 2013, "Mitsubishi Outlander (2nd Generation CW)"),
    ],
    "mitsubishi_raider":  [(2006, 2009, "Mitsubishi Raider (1st Generation)")],
    "mitsubishi_starion": [(1982, 1989, "Mitsubishi Starion (1st Generation)")],
    # ── NISSAN ────────────────────────────────────────────────────────────────
    "nissan_200sx": [
        (1984, 1988, "Nissan 200SX (S12)"),
        (1995, 1998, "Nissan 200SX (B14)"),
    ],
    "nissan_240sx": [
        (1989, 1994, "Nissan 240SX (S13)"),
        (1995, 1998, "Nissan 240SX (S14)"),
    ],
    "nissan_300zx": [
        (1984, 1989, "Nissan 300ZX (Z31)"),
        (1990, 1996, "Nissan 300ZX (Z32)"),
    ],
    "nissan_350z":    [(2003, 2009, "Nissan 350Z (Z33)")],
    "nissan_370z":    [(2009, 2020, "Nissan 370Z (Z34)")],
    "nissan_720":     [(1980, 1986, "Nissan 720 Pickup")],
    "nissan_altima": [
        (1993, 1997, "Nissan Altima (1st Generation L30)"),
        (1998, 2001, "Nissan Altima (2nd Generation L31)"),
        (2002, 2006, "Nissan Altima (3rd Generation L31)"),
        (2007, 2012, "Nissan Altima (4th Generation L32)"),
        (2013, 2018, "Nissan Altima (5th Generation L33)"),
    ],
    "nissan_armada": [
        (2004, 2015, "Nissan Armada (1st Generation TA60)"),
        (2017, 2023, "Nissan Armada (2nd Generation Y62)"),
    ],
    "nissan_cima": [
        (1988, 1991, "Nissan Cima (1st Generation Y31)"),
        (1991, 1996, "Nissan Cima (2nd Generation Y32)"),
    ],
    "nissan_cube":    [(2009, 2014, "Nissan Cube (3rd Generation Z12)")],
    "nissan_d21":     [(1986, 1997, "Nissan Hardbody (D21)")],
    "nissan_frontier": [
        (1998, 2004, "Nissan Frontier (1st Generation D22)"),
        (2005, 2021, "Nissan Frontier (2nd Generation D40)"),
    ],
    "nissan_gtr":     [(2009, 2023, "Nissan GT-R (R35)")],
    "nissan_hardbody":[(1986, 1997, "Nissan Hardbody (D21)")],
    "nissan_juke":    [(2011, 2017, "Nissan Juke (1st Generation F15)")],
    "nissan_leaf":    [(2011, 2017, "Nissan Leaf (1st Generation ZE0)")],
    "nissan_maxima": [
        (1981, 1984, "Nissan Maxima (1st Generation 810)"),
        (1985, 1988, "Nissan Maxima (2nd Generation J30)"),
        (1989, 1994, "Nissan Maxima (3rd Generation J30)"),
        (1995, 1999, "Nissan Maxima (4th Generation A32)"),
        (2000, 2003, "Nissan Maxima (5th Generation A33)"),
        (2004, 2008, "Nissan Maxima (6th Generation A34)"),
        (2009, 2015, "Nissan Maxima (7th Generation A35)"),
    ],
    "nissan_murano": [
        (2003, 2007, "Nissan Murano (1st Generation Z50)"),
        (2009, 2014, "Nissan Murano (2nd Generation Z51)"),
    ],
    "nissan_nv200":   [(2013, 2021, "Nissan NV200 (1st Generation)")],
    "nissan_pathfinder": [
        (1986, 1995, "Nissan Pathfinder (1st Generation WD21)"),
        (1996, 2004, "Nissan Pathfinder (2nd Generation R50)"),
        (2005, 2012, "Nissan Pathfinder (3rd Generation R51)"),
        (2013, 2021, "Nissan Pathfinder (4th Generation R52)"),
    ],
    "nissan_presage": [
        (1998, 2003, "Nissan Presage (1st Generation U30)"),
        (2003, 2009, "Nissan Presage (2nd Generation U31)"),
    ],
    "nissan_pulsar": [
        (1982, 1986, "Nissan Pulsar (N12)"),
        (1987, 1990, "Nissan Pulsar (N13)"),
    ],
    "nissan_quest": [
        (1993, 1998, "Nissan Quest (1st Generation V40)"),
        (1999, 2002, "Nissan Quest (2nd Generation V41)"),
        (2004, 2009, "Nissan Quest (3rd Generation V42)"),
    ],
    "nissan_rogue": [
        (2008, 2013, "Nissan Rogue (1st Generation S35)"),
        (2014, 2020, "Nissan Rogue (2nd Generation T32)"),
    ],
    "nissan_sentra": [
        (1982, 1986, "Nissan Sentra (1st Generation B11)"),
        (1987, 1990, "Nissan Sentra (2nd Generation B12)"),
        (1991, 1994, "Nissan Sentra (3rd Generation B13)"),
        (1995, 1999, "Nissan Sentra (4th Generation B14)"),
        (2000, 2006, "Nissan Sentra (5th Generation B15)"),
        (2007, 2012, "Nissan Sentra (6th Generation B16)"),
    ],
    "nissan_skyline": [
        (1989, 1994, "Nissan Skyline GT-R (R32)"),
        (1995, 1998, "Nissan Skyline GT-R (R33)"),
        (1999, 2002, "Nissan Skyline GT-R (R34)"),
    ],
    "nissan_stanza": [
        (1982, 1986, "Nissan Stanza (T11)"),
        (1987, 1992, "Nissan Stanza (T12)"),
    ],
    "nissan_titan": [
        (2004, 2015, "Nissan Titan (1st Generation A60)"),
        (2016, 2023, "Nissan Titan (2nd Generation A61)"),
    ],
    "nissan_truck":   [(1970, 1986, "Nissan Truck (620/720)")],
    "nissan_versa": [
        (2007, 2011, "Nissan Versa (1st Generation C11)"),
        (2012, 2019, "Nissan Versa (2nd Generation N17)"),
    ],
    "nissan_x-trail": [
        (2001, 2007, "Nissan X-Trail (1st Generation T30)"),
        (2008, 2013, "Nissan X-Trail (2nd Generation T31)"),
    ],
    "nissan_xterra": [
        (1999, 2004, "Nissan Xterra (1st Generation WD22)"),
        (2005, 2015, "Nissan Xterra (2nd Generation N50)"),
    ],
    # ── SCION ─────────────────────────────────────────────────────────────────
    "scion_frs":  [(2013, 2016, "Scion FR-S (ZN6)")],
    "scion_ia":   [(2016, 2016, "Scion iA (1st Generation)")],
    "scion_iq":   [(2012, 2015, "Scion iQ (1st Generation)")],
    "scion_tc": [
        (2005, 2010, "Scion tC (1st Generation ANT10)"),
        (2011, 2016, "Scion tC (2nd Generation AGT20)"),
    ],
    "scion_xa":   [(2004, 2006, "Scion xA (1st Generation NCP61)")],
    "scion_xb": [
        (2004, 2006, "Scion xB (1st Generation NCP31)"),
        (2008, 2015, "Scion xB (2nd Generation AZE151)"),
    ],
    "scion_xd":   [(2008, 2014, "Scion xD (1st Generation NCP115)")],
    # ── SUBARU ────────────────────────────────────────────────────────────────
    "subaru_baja":      [(2003, 2006, "Subaru Baja (1st Generation)")],
    "subaru_brz":       [(2013, 2021, "Subaru BRZ (1st Generation ZC6)")],
    "subaru_crosstrek": [(2013, 2017, "Subaru Crosstrek (1st Generation GP)")],
    "subaru_forester": [
        (1997, 2002, "Subaru Forester (1st Generation SF)"),
        (2003, 2008, "Subaru Forester (2nd Generation SG)"),
        (2009, 2013, "Subaru Forester (3rd Generation SH)"),
        (2014, 2018, "Subaru Forester (4th Generation SJ)"),
    ],
    "subaru_impreza": [
        (1993, 2001, "Subaru Impreza (1st Generation GC/GF)"),
        (2002, 2007, "Subaru Impreza (2nd Generation GD/GG)"),
        (2008, 2011, "Subaru Impreza (3rd Generation GE/GH)"),
        (2012, 2016, "Subaru Impreza (4th Generation GP/GJ)"),
    ],
    "subaru_impreza_wagon": [
        (1993, 2001, "Subaru Impreza Wagon (1st Generation GF)"),
        (2002, 2007, "Subaru Impreza Wagon (2nd Generation GG)"),
        (2008, 2011, "Subaru Impreza Wagon (3rd Generation GH)"),
    ],
    "subaru_legacy": [
        (1990, 1994, "Subaru Legacy (1st Generation BC/BF)"),
        (1995, 1999, "Subaru Legacy (2nd Generation BD/BG)"),
        (2000, 2004, "Subaru Legacy (3rd Generation BE/BH)"),
        (2005, 2009, "Subaru Legacy (4th Generation BL/BP)"),
        (2010, 2014, "Subaru Legacy (5th Generation BM/BR)"),
    ],
    "subaru_outback": [
        (1995, 1999, "Subaru Outback (1st Generation BC/BF)"),
        (2000, 2004, "Subaru Outback (2nd Generation BE/BH)"),
        (2005, 2009, "Subaru Outback (3rd Generation BP/BE)"),
        (2010, 2014, "Subaru Outback (4th Generation BR)"),
    ],
    "subaru_tribeca": [(2006, 2014, "Subaru Tribeca (B9)")],
    "subaru_wrx": [
        (2002, 2007, "Subaru Impreza WRX (2nd Generation GD)"),
        (2008, 2014, "Subaru Impreza WRX (3rd Generation GE/GH)"),
    ],
    # ── SUZUKI ────────────────────────────────────────────────────────────────
    "suzuki_aerio":         [(2002, 2007, "Suzuki Aerio (RC/RB)")],
    "suzuki_boulevard":     [(2005, 2024, "Suzuki Boulevard (M-Series)")],
    "suzuki_equator":       [(2009, 2012, "Suzuki Equator (1st Generation)")],
    "suzuki_esteem":        [(1995, 2002, "Suzuki Esteem (1st Generation)")],
    "suzuki_esteem_wagon":  [(1995, 2002, "Suzuki Esteem Wagon (1st Generation)")],
    "suzuki_forenza":       [(2004, 2008, "Suzuki Forenza (1st Generation)")],
    "suzuki_grand_vitara": [
        (1998, 2005, "Suzuki Grand Vitara (1st Generation FT/HT)"),
        (2006, 2014, "Suzuki Grand Vitara (2nd Generation JT)"),
    ],
    "suzuki_kizashi":       [(2010, 2013, "Suzuki Kizashi (1st Generation)")],
    "suzuki_reno":          [(2005, 2008, "Suzuki Reno (1st Generation)")],
    "suzuki_samurai":       [(1985, 1995, "Suzuki Samurai (SJ)")],
    "suzuki_sidekick":      [(1989, 1998, "Suzuki Sidekick (JA)")],
    "suzuki_swift": [
        (1985, 1994, "Suzuki Swift (1st Generation SF)"),
        (1995, 2001, "Suzuki Swift (2nd Generation SF)"),
    ],
    "suzuki_sx4":           [(2007, 2013, "Suzuki SX4 (1st Generation GY)")],
    "suzuki_verona":        [(2004, 2006, "Suzuki Verona (1st Generation)")],
    "suzuki_vitara":        [(1989, 1999, "Suzuki Vitara (1st Generation ET)")],
    "suzuki_x90":           [(1995, 1998, "Suzuki X-90 (EL)")],
    "suzuki_xl7": [
        (2001, 2006, "Suzuki XL7 (1st Generation FT/HT)"),
        (2007, 2009, "Suzuki XL7 (2nd Generation JT)"),
    ],
    # ── TOYOTA ────────────────────────────────────────────────────────────────
    "toyota_1-ton truck": [(1947, 1964, "Toyota 1-Ton Truck (FA/FB)")],
    "toyota_4runner": [
        (1984, 1989, "Toyota 4Runner (1st Generation N60)"),
        (1990, 1995, "Toyota 4Runner (2nd Generation N120/N130)"),
        (1996, 2002, "Toyota 4Runner (3rd Generation N180)"),
        (2003, 2009, "Toyota 4Runner (4th Generation N210)"),
        (2010, 2023, "Toyota 4Runner (5th Generation N280)"),
    ],
    "toyota_aristo": [
        (1991, 1997, "Toyota Aristo (1st Generation Z10)"),
        (1997, 2004, "Toyota Aristo (2nd Generation Z20)"),
    ],
    "toyota_avalon": [
        (1995, 1999, "Toyota Avalon (1st Generation XX10)"),
        (2000, 2004, "Toyota Avalon (2nd Generation XX20)"),
        (2005, 2012, "Toyota Avalon (3rd Generation XX30)"),
    ],
    "toyota_camry": [
        (1983, 1986, "Toyota Camry (1st Generation V10)"),
        (1987, 1991, "Toyota Camry (2nd Generation V20)"),
        (1992, 1996, "Toyota Camry (3rd Generation V30)"),
        (1997, 2001, "Toyota Camry (4th Generation XV20)"),
        (2002, 2006, "Toyota Camry (5th Generation XV30)"),
        (2007, 2011, "Toyota Camry (6th Generation XV40)"),
        (2012, 2017, "Toyota Camry (7th Generation XV50)"),
    ],
    "toyota_camry_le": [
        (1992, 1996, "Toyota Camry (3rd Generation V30)"),
        (1997, 2001, "Toyota Camry (4th Generation XV20)"),
        (2002, 2006, "Toyota Camry (5th Generation XV30)"),
        (2007, 2011, "Toyota Camry (6th Generation XV40)"),
        (2012, 2017, "Toyota Camry (7th Generation XV50)"),
    ],
    "toyota_camry_se": [
        (1997, 2001, "Toyota Camry (4th Generation XV20)"),
        (2002, 2006, "Toyota Camry (5th Generation XV30)"),
        (2007, 2011, "Toyota Camry (6th Generation XV40)"),
        (2012, 2017, "Toyota Camry (7th Generation XV50)"),
    ],
    "toyota_camry_xle": [
        (1997, 2001, "Toyota Camry (4th Generation XV20)"),
        (2002, 2006, "Toyota Camry (5th Generation XV30)"),
        (2007, 2011, "Toyota Camry (6th Generation XV40)"),
        (2012, 2017, "Toyota Camry (7th Generation XV50)"),
    ],
    "toyota_camry_solara": [
        (1999, 2003, "Toyota Camry Solara (1st Generation XV20)"),
        (2004, 2008, "Toyota Camry Solara (2nd Generation XV30)"),
    ],
    "toyota_camry_solara_convertible": [
        (1999, 2003, "Toyota Camry Solara Convertible (1st Generation XV20)"),
        (2004, 2008, "Toyota Camry Solara Convertible (2nd Generation XV30)"),
    ],
    "toyota_celica": [
        (1971, 1977, "Toyota Celica (1st Generation A20)"),
        (1978, 1981, "Toyota Celica (2nd Generation A40)"),
        (1982, 1985, "Toyota Celica (3rd Generation A60)"),
        (1986, 1989, "Toyota Celica (4th Generation T160)"),
        (1990, 1993, "Toyota Celica (5th Generation T180)"),
        (1994, 1999, "Toyota Celica (6th Generation T200)"),
        (2000, 2006, "Toyota Celica (7th Generation T230)"),
    ],
    "toyota_celica_convertible": [
        (1990, 1993, "Toyota Celica Convertible (5th Generation T180)"),
        (1994, 1999, "Toyota Celica Convertible (6th Generation T200)"),
    ],
    "toyota_corolla": [
        (1966, 1970, "Toyota Corolla (1st Generation E10)"),
        (1971, 1974, "Toyota Corolla (2nd Generation E20)"),
        (1975, 1979, "Toyota Corolla (3rd Generation E30)"),
        (1980, 1983, "Toyota Corolla (4th Generation E70)"),
        (1984, 1987, "Toyota Corolla (5th Generation E80)"),
        (1988, 1992, "Toyota Corolla (6th Generation E90)"),
        (1993, 1997, "Toyota Corolla (7th Generation E100)"),
        (1998, 2002, "Toyota Corolla (8th Generation E110)"),
        (2003, 2008, "Toyota Corolla (9th Generation E130)"),
        (2009, 2013, "Toyota Corolla (10th Generation E140)"),
    ],
    "toyota_corolla_ce": [
        (1993, 1997, "Toyota Corolla (7th Generation E100)"),
        (1998, 2002, "Toyota Corolla (8th Generation E110)"),
        (2003, 2008, "Toyota Corolla (9th Generation E130)"),
    ],
    "toyota_corolla_dx": [
        (1988, 1992, "Toyota Corolla (6th Generation E90)"),
        (1993, 1997, "Toyota Corolla (7th Generation E100)"),
    ],
    "toyota_corolla_le": [
        (1993, 1997, "Toyota Corolla (7th Generation E100)"),
        (1998, 2002, "Toyota Corolla (8th Generation E110)"),
        (2003, 2008, "Toyota Corolla (9th Generation E130)"),
        (2009, 2013, "Toyota Corolla (10th Generation E140)"),
    ],
    "toyota_corolla_s": [
        (2003, 2008, "Toyota Corolla (9th Generation E130)"),
        (2009, 2013, "Toyota Corolla (10th Generation E140)"),
    ],
    "toyota_corolla_wagon": [(1988, 1992, "Toyota Corolla Wagon (6th Generation E90)")],
    "toyota_cressida": [
        (1977, 1980, "Toyota Cressida (1st Generation X30)"),
        (1981, 1984, "Toyota Cressida (2nd Generation X50/X60)"),
        (1985, 1988, "Toyota Cressida (3rd Generation X70)"),
        (1989, 1992, "Toyota Cressida (4th Generation X80)"),
    ],
    "toyota_echo":    [(2000, 2005, "Toyota Echo (P10)")],
    "toyota_estima": [
        (1990, 1999, "Toyota Estima (1st Generation R10/R20)"),
        (2000, 2019, "Toyota Estima (2nd Generation R30/R40)"),
    ],
    "toyota_fj40":    [(1960, 1984, "Toyota FJ40 Land Cruiser")],
    "toyota_fjcruiser":[(2006, 2014, "Toyota FJ Cruiser (GSJ15)")],
    "toyota_flatbed": [(1947, 1969, "Toyota Flatbed Truck")],
    "toyota_fortuner":[(2005, 2015, "Toyota Fortuner (1st Generation AN50)")],
    "toyota_hiace": [
        (1967, 1982, "Toyota Hiace (1st/2nd Generation H10/H20)"),
        (1983, 1989, "Toyota Hiace (3rd Generation H50)"),
        (1989, 2004, "Toyota Hiace (4th Generation H100)"),
        (2004, 2019, "Toyota Hiace (5th Generation H200)"),
    ],
    "toyota_highlander": [
        (2001, 2007, "Toyota Highlander (1st Generation XU20)"),
        (2008, 2013, "Toyota Highlander (2nd Generation XU40)"),
    ],
    "toyota_hilux": [
        (1968, 1972, "Toyota Hilux (1st Generation N10)"),
        (1973, 1978, "Toyota Hilux (2nd Generation N20)"),
        (1979, 1983, "Toyota Hilux (3rd Generation N30/N40)"),
        (1984, 1988, "Toyota Hilux (4th Generation N50/N60)"),
        (1989, 1997, "Toyota Hilux (5th/6th Generation N80/N90)"),
        (1998, 2005, "Toyota Hilux (7th Generation N140/N150)"),
        (2005, 2015, "Toyota Hilux (7th Generation N200)"),
    ],
    "toyota_landcruiser": [
        (1960, 1984, "Toyota Land Cruiser (FJ40/FJ55)"),
        (1980, 1987, "Toyota Land Cruiser (FJ60)"),
        (1988, 1997, "Toyota Land Cruiser (FJ80)"),
        (1998, 2007, "Toyota Land Cruiser (100-Series)"),
        (2008, 2021, "Toyota Land Cruiser (200-Series)"),
    ],
    "toyota_matrix": [
        (2003, 2008, "Toyota Matrix (1st Generation E130)"),
        (2009, 2014, "Toyota Matrix (2nd Generation E140)"),
    ],
    "toyota_mr2": [
        (1984, 1989, "Toyota MR2 (1st Generation AW11)"),
        (1990, 1999, "Toyota MR2 (2nd Generation SW20)"),
        (2000, 2007, "Toyota MR2 Spyder (3rd Generation ZZW30)"),
    ],
    "toyota_paseo": [
        (1992, 1997, "Toyota Paseo (1st Generation EL44)"),
        (1998, 1999, "Toyota Paseo (2nd Generation EL54)"),
    ],
    "toyota_pickup": [
        (1969, 1978, "Toyota Pickup (1st/2nd Generation)"),
        (1979, 1983, "Toyota Pickup (3rd Generation N30)"),
        (1984, 1988, "Toyota Pickup (4th Generation N50/N60)"),
        (1989, 1995, "Toyota Pickup (5th Generation N80)"),
    ],
    "toyota_previa":  [(1990, 1997, "Toyota Previa (1st Generation R10/R20)")],
    "toyota_prius": [
        (2001, 2003, "Toyota Prius (1st Generation NHW10/NHW11)"),
        (2004, 2009, "Toyota Prius (2nd Generation NHW20)"),
        (2010, 2015, "Toyota Prius (3rd Generation ZVW30)"),
    ],
    "toyota_rav4": [
        (1994, 2000, "Toyota RAV4 (1st Generation XA10)"),
        (2001, 2005, "Toyota RAV4 (2nd Generation XA20)"),
        (2006, 2012, "Toyota RAV4 (3rd Generation XA30)"),
        (2013, 2018, "Toyota RAV4 (4th Generation XA40)"),
    ],
    "toyota_sequoia": [
        (2001, 2007, "Toyota Sequoia (1st Generation XK30/XK40)"),
        (2008, 2022, "Toyota Sequoia (2nd Generation XK60)"),
    ],
    "toyota_sienna": [
        (1998, 2003, "Toyota Sienna (1st Generation XL10)"),
        (2004, 2010, "Toyota Sienna (2nd Generation XL20)"),
        (2011, 2020, "Toyota Sienna (3rd Generation XL30)"),
    ],
    "toyota_solara": [
        (1999, 2003, "Toyota Camry Solara (1st Generation XV20)"),
        (2004, 2008, "Toyota Camry Solara (2nd Generation XV30)"),
    ],
    "toyota_solara_convertable": [
        (1999, 2003, "Toyota Camry Solara Convertible (1st Generation XV20)"),
        (2004, 2008, "Toyota Camry Solara Convertible (2nd Generation XV30)"),
    ],
    "toyota_solara_convertible": [
        (1999, 2003, "Toyota Camry Solara Convertible (1st Generation XV20)"),
        (2004, 2008, "Toyota Camry Solara Convertible (2nd Generation XV30)"),
    ],
    "toyota_starlet": [
        (1973, 1978, "Toyota Starlet (1st Generation KP30)"),
        (1978, 1984, "Toyota Starlet (2nd Generation KP60)"),
        (1984, 1989, "Toyota Starlet (3rd Generation KP70)"),
    ],
    "toyota_supra": [
        (1978, 1981, "Toyota Supra (1st Generation A40)"),
        (1982, 1986, "Toyota Supra (2nd Generation A60)"),
        (1987, 1993, "Toyota Supra (3rd Generation A70)"),
        (1994, 2002, "Toyota Supra (4th Generation A80)"),
    ],
    "toyota_t100":    [(1993, 1998, "Toyota T100 (N120/N130)")],
    "toyota_tacoma": [
        (1995, 2004, "Toyota Tacoma (1st Generation N140/N150)"),
        (2005, 2015, "Toyota Tacoma (2nd Generation N200)"),
    ],
    "toyota_tercel": [
        (1978, 1982, "Toyota Tercel (1st Generation AL10)"),
        (1983, 1988, "Toyota Tercel (2nd Generation AL20)"),
        (1991, 1994, "Toyota Tercel (3rd Generation EL40)"),
        (1995, 1999, "Toyota Tercel (4th Generation EL50)"),
    ],
    "toyota_tiara":   [(1960, 1964, "Toyota Tiara (1st Generation)")],
    "toyota_tundra": [
        (2000, 2006, "Toyota Tundra (1st Generation UCK/NDK)"),
        (2007, 2021, "Toyota Tundra (2nd Generation USK/GSK)"),
    ],
    "toyota_van":     [(1984, 1989, "Toyota Van (R20)")],
    "toyota_venza":   [(2009, 2015, "Toyota Venza (1st Generation AGV)")],
    "toyota_yaris": [
        (2007, 2011, "Toyota Yaris (2nd Generation XP90)"),
        (2012, 2018, "Toyota Yaris (3rd Generation XP130)"),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# AMERICAN MAP  (to be filled by agent)
# ─────────────────────────────────────────────────────────────────────────────
AMERICAN_MAP = {
    # ── AMC ───────────────────────────────────────────────────────────────────
    "amc_ambassador":  [(1958, 1974, "AMC Ambassador")],
    "amc_amx": [
        (1968, 1970, "AMC AMX (1st Generation)"),
        (1971, 1974, "AMC AMX (2nd Generation)"),
    ],
    "amc_eagle":       [(1980, 1988, "AMC Eagle (1st Generation)")],
    "amc_eagle_wagon": [(1980, 1988, "AMC Eagle Wagon (1st Generation)")],
    "amc_hornet":      [(1970, 1977, "AMC Hornet (1st Generation)")],
    "amc_javelin": [
        (1968, 1970, "AMC Javelin (1st Generation)"),
        (1971, 1974, "AMC Javelin (2nd Generation)"),
    ],
    "amc_rambler":     [(1950, 1969, "AMC Rambler")],
    # ── BUICK ─────────────────────────────────────────────────────────────────
    "buick_apollo":        [(1973, 1975, "Buick Apollo (A-body)")],
    "buick_centurion":     [(1971, 1973, "Buick Centurion (C-body)")],
    "buick_century": [
        (1973, 1977, "Buick Century (A-body)"),
        (1982, 1996, "Buick Century (A-body 2nd Generation)"),
        (1997, 2005, "Buick Century (W-body 3rd Generation)"),
    ],
    "buick_electra": [
        (1959, 1984, "Buick Electra (C-body)"),
        (1985, 1990, "Buick Electra (C-body 5th Generation)"),
    ],
    "buick_enclave":       [(2008, 2017, "Buick Enclave (1st Generation GMT351)")],
    "buick_encore":        [(2013, 2019, "Buick Encore (1st Generation)")],
    "buick_grand national":[(1982, 1987, "Buick Grand National (G-body)")],
    "buick_gs":            [(1965, 1975, "Buick GS/Gran Sport (A-body)")],
    "buick_invicta":       [(1959, 1963, "Buick Invicta (1st Generation)")],
    "buick_lacrosse": [
        (2005, 2009, "Buick LaCrosse (1st Generation W-body)"),
        (2010, 2016, "Buick LaCrosse (2nd Generation W-body)"),
    ],
    "buick_lesabre": [
        (1959, 1964, "Buick LeSabre (1st/2nd Generation)"),
        (1965, 1970, "Buick LeSabre (3rd/4th Generation)"),
        (1971, 1976, "Buick LeSabre (5th Generation B-body)"),
        (1977, 1985, "Buick LeSabre (6th Generation B-body)"),
        (1986, 1991, "Buick LeSabre (7th Generation H-body)"),
        (1992, 1999, "Buick LeSabre (7th Generation H-body)"),
        (2000, 2005, "Buick LeSabre (8th Generation H-body)"),
    ],
    "buick_lucerne":       [(2006, 2011, "Buick Lucerne (H-body)")],
    "buick_parkavenue": [
        (1991, 1996, "Buick Park Avenue (1st Generation C-body)"),
        (1997, 2005, "Buick Park Avenue (2nd Generation C-body)"),
    ],
    "buick_rainier":       [(2004, 2007, "Buick Rainier (GMT360)")],
    "buick_reatta":        [(1988, 1991, "Buick Reatta (1st Generation)")],
    "buick_regal": [
        (1973, 1977, "Buick Regal (1st Generation A-body)"),
        (1978, 1987, "Buick Regal (2nd/3rd Generation A/G-body)"),
        (1988, 1996, "Buick Regal (4th Generation W-body)"),
        (1997, 2004, "Buick Regal (5th Generation W-body)"),
    ],
    "buick_rendezvous":    [(2002, 2007, "Buick Rendezvous (1st Generation)")],
    "buick_riviera": [
        (1963, 1965, "Buick Riviera (1st Generation)"),
        (1966, 1970, "Buick Riviera (2nd Generation)"),
        (1971, 1973, "Buick Riviera (3rd Generation)"),
        (1979, 1985, "Buick Riviera (6th Generation E-body)"),
        (1986, 1993, "Buick Riviera (7th Generation E-body)"),
        (1995, 1999, "Buick Riviera (8th Generation E-body)"),
    ],
    "buick_roadmaster":    [(1991, 1996, "Buick Roadmaster (B-body)")],
    "buick_skylark": [
        (1953, 1954, "Buick Skylark (1st Generation)"),
        (1961, 1972, "Buick Skylark (Y-body)"),
        (1975, 1980, "Buick Skylark (X-body)"),
        (1980, 1985, "Buick Skylark (X-body 3rd Generation)"),
        (1986, 1991, "Buick Skylark (N-body)"),
        (1992, 1998, "Buick Skylark (N-body 6th Generation)"),
    ],
    "buick_special":       [(1961, 1963, "Buick Special (Y-body)")],
    "buick_super":         [(1940, 1958, "Buick Super (Classic)")],
    "buick_t type":        [(1983, 1987, "Buick T-Type (G-body)")],
    "buick_terraza":       [(2005, 2007, "Buick Terraza (U-body)")],
    "buick_ultra": [
        (1990, 1996, "Buick Park Avenue Ultra (1st Generation)"),
        (1997, 2005, "Buick Park Avenue Ultra (2nd Generation)"),
    ],
    "buick_verano":        [(2012, 2017, "Buick Verano (1st Generation)")],
    "buick_wildcat":       [(1963, 1970, "Buick Wildcat (C-body)")],
    # ── CADILLAC ──────────────────────────────────────────────────────────────
    "cadillac_allante":    [(1987, 1993, "Cadillac Allante (1st Generation)")],
    "cadillac_ats":        [(2013, 2019, "Cadillac ATS (1st Generation)")],
    "cadillac_brougham":   [(1987, 1992, "Cadillac Brougham (D-body)")],
    "cadillac_calais":     [(1965, 1976, "Cadillac Calais (C-body)")],
    "cadillac_catera":     [(1997, 2001, "Cadillac Catera (1st Generation)")],
    "cadillac_cimarron":   [(1981, 1988, "Cadillac Cimarron (J-body)")],
    "cadillac_cts": [
        (2003, 2007, "Cadillac CTS (1st Generation)"),
        (2008, 2013, "Cadillac CTS (2nd Generation)"),
        (2014, 2019, "Cadillac CTS (3rd Generation)"),
    ],
    "cadillac_cts_wagon":  [(2010, 2014, "Cadillac CTS Wagon (2nd Generation)")],
    "cadillac_deville": [
        (1959, 1964, "Cadillac DeVille (1st/2nd Generation)"),
        (1965, 1970, "Cadillac DeVille (3rd/4th Generation)"),
        (1971, 1976, "Cadillac DeVille (5th Generation)"),
        (1977, 1984, "Cadillac DeVille (6th Generation)"),
        (1985, 1993, "Cadillac DeVille (7th Generation)"),
        (1994, 1999, "Cadillac DeVille (8th Generation)"),
        (2000, 2005, "Cadillac DeVille (9th Generation)"),
    ],
    "cadillac_eldorado": [
        (1953, 1966, "Cadillac Eldorado (1st-5th Generation)"),
        (1967, 1978, "Cadillac Eldorado (6th/7th Generation)"),
        (1979, 1985, "Cadillac Eldorado (8th Generation E-body)"),
        (1986, 1991, "Cadillac Eldorado (9th Generation E-body)"),
        (1992, 2002, "Cadillac Eldorado (10th/11th Generation)"),
    ],
    "cadillac_escalade": [
        (1999, 2000, "Cadillac Escalade (1st Generation GMT400)"),
        (2002, 2006, "Cadillac Escalade (2nd Generation GMT800)"),
        (2007, 2014, "Cadillac Escalade (3rd Generation GMT900)"),
    ],
    "cadillac_fleetwood": [
        (1976, 1992, "Cadillac Fleetwood (C/D-body)"),
        (1993, 1996, "Cadillac Fleetwood (B-body)"),
    ],
    "cadillac_hearse":     [(1970, 2010, "Cadillac Hearse/Professional Car")],
    "cadillac_seville": [
        (1975, 1979, "Cadillac Seville (1st Generation)"),
        (1980, 1985, "Cadillac Seville (2nd Generation)"),
        (1986, 1991, "Cadillac Seville (3rd Generation)"),
        (1992, 1997, "Cadillac Seville (4th Generation)"),
        (1998, 2004, "Cadillac Seville (5th Generation)"),
    ],
    "cadillac_srx": [
        (2004, 2009, "Cadillac SRX (1st Generation)"),
        (2010, 2016, "Cadillac SRX (2nd Generation)"),
    ],
    "cadillac_sts":        [(2005, 2011, "Cadillac STS (1st Generation)")],
    "cadillac_xlr":        [(2004, 2009, "Cadillac XLR (1st Generation)")],
    "cadillac_xts":        [(2013, 2019, "Cadillac XTS (1st Generation)")],
    # ── CHEVROLET ─────────────────────────────────────────────────────────────
    "chevrolet_1 ton":     [(1960, 1987, "Chevrolet 1-Ton Truck (C/K-Series)")],
    "chevrolet_210":       [(1953, 1957, "Chevrolet 210 (2nd Series)")],
    "chevrolet_3100":      [(1947, 1955, "Chevrolet 3100 (Advance Design)")],
    "chevrolet_3600":      [(1947, 1955, "Chevrolet 3600 (Advance Design)")],
    "chevrolet_apache":    [(1958, 1961, "Chevrolet Apache (Task Force)")],
    "chevrolet_astro": [
        (1985, 1994, "Chevrolet Astro (1st Generation)"),
        (1995, 2005, "Chevrolet Astro (2nd Generation)"),
    ],
    "chevrolet_avalanche": [
        (2002, 2006, "Chevrolet Avalanche (1st Generation GMT800)"),
        (2007, 2013, "Chevrolet Avalanche (2nd Generation GMT900)"),
    ],
    "chevrolet_aveo": [
        (2004, 2008, "Chevrolet Aveo (1st Generation T200)"),
        (2009, 2011, "Chevrolet Aveo (2nd Generation T250)"),
    ],
    "chevrolet_bel air": [
        (1950, 1954, "Chevrolet Bel Air (1st Generation)"),
        (1955, 1957, "Chevrolet Bel Air (2nd Generation)"),
        (1958, 1960, "Chevrolet Bel Air (3rd Generation)"),
        (1961, 1964, "Chevrolet Bel Air (4th Generation)"),
    ],
    "chevrolet_beretta":   [(1987, 1996, "Chevrolet Beretta (L-body)")],
    "chevrolet_blazer": [
        (1969, 1972, "Chevrolet Blazer (1st Generation K5)"),
        (1973, 1991, "Chevrolet Blazer (2nd Generation K5)"),
        (1983, 1994, "Chevrolet S-10 Blazer (S-body 1st Generation)"),
        (1995, 2005, "Chevrolet Blazer (S-body 2nd Generation)"),
    ],
    "chevrolet_bonanza":   [(1970, 1972, "Chevrolet C/K Bonanza")],
    "chevrolet_c-k1500": [
        (1960, 1966, "Chevrolet C/K (1st Generation)"),
        (1967, 1972, "Chevrolet C/K (2nd Generation)"),
        (1973, 1987, "Chevrolet C/K (3rd Generation)"),
        (1988, 1998, "Chevrolet C/K (4th Generation)"),
    ],
    "chevrolet_c-k2500": [
        (1960, 1966, "Chevrolet C/K (1st Generation)"),
        (1967, 1972, "Chevrolet C/K (2nd Generation)"),
        (1973, 1987, "Chevrolet C/K (3rd Generation)"),
        (1988, 2000, "Chevrolet C/K (4th Generation)"),
    ],
    "chevrolet_c-k3500": [
        (1960, 1966, "Chevrolet C/K (1st Generation)"),
        (1967, 1972, "Chevrolet C/K (2nd Generation)"),
        (1973, 1987, "Chevrolet C/K (3rd Generation)"),
        (1988, 2000, "Chevrolet C/K (4th Generation)"),
    ],
    "chevrolet_c10": [
        (1960, 1966, "Chevrolet C10 (1st Generation)"),
        (1967, 1972, "Chevrolet C10 (2nd Generation)"),
        (1973, 1987, "Chevrolet C10 (3rd Generation)"),
    ],
    "chevrolet_c20": [
        (1960, 1966, "Chevrolet C20 (1st Generation)"),
        (1967, 1972, "Chevrolet C20 (2nd Generation)"),
        (1973, 1987, "Chevrolet C20 (3rd Generation)"),
    ],
    "chevrolet_c30": [
        (1960, 1966, "Chevrolet C30 (1st Generation)"),
        (1967, 1972, "Chevrolet C30 (2nd Generation)"),
        (1973, 1988, "Chevrolet C30 (3rd Generation)"),
    ],
    "chevrolet_c5500":     [(1990, 2009, "Chevrolet C5500 (Medium Duty)")],
    "chevrolet_c60":       [(1960, 1990, "Chevrolet C60 (Medium Duty)")],
    "chevrolet_c65":       [(1965, 1990, "Chevrolet C65 (Medium Duty)")],
    "chevrolet_c6500":     [(1990, 2009, "Chevrolet C6500 (Medium Duty)")],
    "chevrolet_camaro": [
        (1967, 1969, "Chevrolet Camaro (1st Generation F-body)"),
        (1970, 1981, "Chevrolet Camaro (2nd Generation F-body)"),
        (1982, 1992, "Chevrolet Camaro (3rd Generation F-body)"),
        (1993, 2002, "Chevrolet Camaro (4th Generation F-body)"),
        (2010, 2015, "Chevrolet Camaro (5th Generation)"),
    ],
    "chevrolet_caprice": [
        (1966, 1970, "Chevrolet Caprice (1st Generation B-body)"),
        (1971, 1976, "Chevrolet Caprice (2nd Generation B-body)"),
        (1977, 1990, "Chevrolet Caprice (3rd Generation B-body)"),
        (1991, 1996, "Chevrolet Caprice (4th Generation B-body)"),
    ],
    "chevrolet_captiva":   [(2006, 2011, "Chevrolet Captiva (1st Generation)")],
    "chevrolet_cavalier": [
        (1982, 1994, "Chevrolet Cavalier (1st Generation J-body)"),
        (1995, 2005, "Chevrolet Cavalier (3rd Generation J-body)"),
    ],
    "chevrolet_celebrity": [(1982, 1990, "Chevrolet Celebrity (A-body)")],
    "chevrolet_chevelle": [
        (1964, 1967, "Chevrolet Chevelle (1st Generation A-body)"),
        (1968, 1972, "Chevrolet Chevelle (2nd Generation A-body)"),
        (1973, 1977, "Chevrolet Chevelle (3rd Generation A-body)"),
    ],
    "chevrolet_chevette":  [(1976, 1987, "Chevrolet Chevette (T-body)")],
    "chevrolet_cheyenne": [
        (1971, 1987, "Chevrolet Cheyenne (C/K 3rd Generation)"),
        (1988, 1998, "Chevrolet Cheyenne (C/K 4th Generation)"),
    ],
    "chevrolet_classic":   [(2004, 2005, "Chevrolet Classic (1st Generation)")],
    "chevrolet_cobalt":    [(2005, 2010, "Chevrolet Cobalt (Delta)")],
    "chevrolet_colorado": [
        (2004, 2012, "Chevrolet Colorado (1st Generation GMT355)"),
        (2015, 2022, "Chevrolet Colorado (2nd Generation K2XX)"),
    ],
    "chevrolet_corsica":   [(1987, 1996, "Chevrolet Corsica (L-body)")],
    "chevrolet_corvair": [
        (1960, 1964, "Chevrolet Corvair (1st Generation Y-body)"),
        (1965, 1969, "Chevrolet Corvair (2nd Generation Y-body)"),
    ],
    "chevrolet_corvette": [
        (1953, 1962, "Chevrolet Corvette (C1)"),
        (1963, 1967, "Chevrolet Corvette (C2)"),
        (1968, 1982, "Chevrolet Corvette (C3)"),
        (1984, 1996, "Chevrolet Corvette (C4)"),
        (1997, 2004, "Chevrolet Corvette (C5)"),
        (2005, 2013, "Chevrolet Corvette (C6)"),
    ],
    "chevrolet_cruze": [
        (2011, 2015, "Chevrolet Cruze (1st Generation J300)"),
        (2016, 2019, "Chevrolet Cruze (2nd Generation J300)"),
    ],
    "chevrolet_delray":    [(1954, 1958, "Chevrolet Del Ray")],
    "chevrolet_deluxe":    [(1941, 1952, "Chevrolet Deluxe")],
    "chevrolet_el camino": [
        (1959, 1960, "Chevrolet El Camino (1st Generation)"),
        (1964, 1967, "Chevrolet El Camino (2nd Generation A-body)"),
        (1968, 1972, "Chevrolet El Camino (3rd Generation A-body)"),
        (1973, 1977, "Chevrolet El Camino (4th Generation A-body)"),
        (1978, 1987, "Chevrolet El Camino (5th Generation A/G-body)"),
    ],
    "chevrolet_equinox": [
        (2005, 2009, "Chevrolet Equinox (1st Generation Theta)"),
        (2010, 2017, "Chevrolet Equinox (2nd Generation Theta+)"),
    ],
    "chevrolet_express": [
        (1996, 2002, "Chevrolet Express (1st Generation GMT600)"),
        (2003, 2021, "Chevrolet Express (2nd Generation)"),
    ],
    "chevrolet_fleetline":   [(1941, 1952, "Chevrolet Fleetline")],
    "chevrolet_fleetmaster": [(1941, 1948, "Chevrolet Fleetmaster")],
    "chevrolet_fleetside": [
        (1960, 1966, "Chevrolet Fleetside (C/K 1st Generation)"),
        (1967, 1987, "Chevrolet Fleetside (C/K 2nd/3rd Generation)"),
    ],
    "chevrolet_g10":       [(1964, 1995, "Chevrolet G10 Van (G-Series)")],
    "chevrolet_g20":       [(1964, 1995, "Chevrolet G20 Van (G-Series)")],
    "chevrolet_g30":       [(1964, 1995, "Chevrolet G30 Van (G-Series)")],
    "chevrolet_hhr":       [(2006, 2011, "Chevrolet HHR (Delta)")],
    "chevrolet_impala": [
        (1958, 1960, "Chevrolet Impala (1st Generation)"),
        (1961, 1964, "Chevrolet Impala (2nd Generation)"),
        (1965, 1970, "Chevrolet Impala (3rd/4th Generation)"),
        (1971, 1976, "Chevrolet Impala (5th Generation)"),
        (1977, 1985, "Chevrolet Impala (6th Generation)"),
        (2000, 2005, "Chevrolet Impala (7th Generation W-body)"),
        (2006, 2013, "Chevrolet Impala (8th Generation W-body)"),
    ],
    "chevrolet_k10": [
        (1960, 1966, "Chevrolet K10 (1st Generation)"),
        (1967, 1972, "Chevrolet K10 (2nd Generation)"),
        (1973, 1987, "Chevrolet K10 (3rd Generation)"),
    ],
    "chevrolet_k20": [
        (1960, 1966, "Chevrolet K20 (1st Generation)"),
        (1967, 1972, "Chevrolet K20 (2nd Generation)"),
        (1973, 1987, "Chevrolet K20 (3rd Generation)"),
    ],
    "chevrolet_kodiak":    [(1980, 2009, "Chevrolet Kodiak (Commercial Truck)")],
    "chevrolet_lumina": [
        (1990, 1994, "Chevrolet Lumina (1st Generation W-body)"),
        (1995, 2001, "Chevrolet Lumina (2nd Generation W-body)"),
    ],
    "chevrolet_malibu": [
        (1964, 1967, "Chevrolet Malibu (1st Generation A-body)"),
        (1968, 1972, "Chevrolet Malibu (2nd Generation A-body)"),
        (1973, 1977, "Chevrolet Malibu (3rd Generation A-body)"),
        (1997, 2003, "Chevrolet Malibu (4th Generation N-body)"),
        (2004, 2007, "Chevrolet Malibu (5th Generation Epsilon)"),
        (2008, 2012, "Chevrolet Malibu (6th Generation Epsilon+)"),
    ],
    "chevrolet_metro":     [(1989, 2001, "Chevrolet Metro (1st/2nd Generation)")],
    "chevrolet_montecarlo": [
        (1970, 1972, "Chevrolet Monte Carlo (1st Generation A-body)"),
        (1973, 1977, "Chevrolet Monte Carlo (2nd Generation A-body)"),
        (1978, 1988, "Chevrolet Monte Carlo (3rd/4th Generation A/G-body)"),
        (1995, 2005, "Chevrolet Monte Carlo (5th/6th Generation W-body)"),
    ],
    "chevrolet_monza":     [(1975, 1980, "Chevrolet Monza (H-body)")],
    "chevrolet_nomad":     [(1955, 1957, "Chevrolet Nomad (1st Generation)")],
    "chevrolet_nova": [
        (1962, 1965, "Chevrolet Nova/Chevy II (1st Generation X-body)"),
        (1966, 1967, "Chevrolet Nova (2nd Generation X-body)"),
        (1968, 1974, "Chevrolet Nova (3rd Generation X-body)"),
        (1975, 1979, "Chevrolet Nova (4th Generation X-body)"),
    ],
    "chevrolet_optra":     [(2004, 2008, "Chevrolet Optra (1st Generation)")],
    "chevrolet_orlando":   [(2012, 2014, "Chevrolet Orlando (1st Generation)")],
    "chevrolet_pickup": [
        (1947, 1954, "Chevrolet Pickup (Advance Design)"),
        (1955, 1959, "Chevrolet Pickup (Task Force)"),
    ],
    "chevrolet_prizm":     [(1998, 2002, "Chevrolet Prizm (E-Series)")],
    "chevrolet_s10": [
        (1982, 1993, "Chevrolet S-10 (1st Generation)"),
        (1994, 2004, "Chevrolet S-10 (2nd Generation)"),
    ],
    "chevrolet_scottsdale": [(1975, 1991, "Chevrolet Scottsdale (C/K)")],
    "chevrolet_sierra":    [(1973, 1987, "Chevrolet Sierra (C/K 3rd Generation)")],
    "chevrolet_silverado": [
        (1999, 2006, "Chevrolet Silverado (1st Generation GMT800)"),
        (2007, 2013, "Chevrolet Silverado (2nd Generation GMT900)"),
        (2014, 2018, "Chevrolet Silverado (3rd Generation K2XX)"),
    ],
    "chevrolet_silverado_3500": [
        (1999, 2006, "Chevrolet Silverado 3500 (1st Generation GMT800)"),
        (2007, 2013, "Chevrolet Silverado 3500 (2nd Generation GMT900)"),
        (2014, 2018, "Chevrolet Silverado 3500 (3rd Generation K2XX)"),
    ],
    "chevrolet_sonic":     [(2012, 2020, "Chevrolet Sonic (Gamma II)")],
    "chevrolet_spark":     [(2013, 2022, "Chevrolet Spark (2nd Generation M400)")],
    "chevrolet_ss":        [(2014, 2017, "Chevrolet SS (1st Generation)")],
    "chevrolet_ssr":       [(2003, 2006, "Chevrolet SSR (1st Generation)")],
    "chevrolet_stepside": [
        (1955, 1966, "Chevrolet Stepside (Task Force/1st Generation)"),
        (1967, 1987, "Chevrolet Stepside (C/K 2nd/3rd Generation)"),
    ],
    "chevrolet_styleline": [(1949, 1952, "Chevrolet Styleline")],
    "chevrolet_stylemaster":[(1941, 1948, "Chevrolet Stylemaster")],
    "chevrolet_suburban": [
        (1947, 1966, "Chevrolet Suburban (1st-4th Generation)"),
        (1967, 1972, "Chevrolet Suburban (5th Generation)"),
        (1973, 1991, "Chevrolet Suburban (6th/7th Generation)"),
        (1992, 1999, "Chevrolet Suburban (8th Generation GMT400)"),
        (2000, 2006, "Chevrolet Suburban (9th Generation GMT800)"),
        (2007, 2014, "Chevrolet Suburban (10th Generation GMT900)"),
    ],
    "chevrolet_tahoe": [
        (1995, 1999, "Chevrolet Tahoe (1st Generation GMT410)"),
        (2000, 2006, "Chevrolet Tahoe (2nd Generation GMT800)"),
        (2007, 2014, "Chevrolet Tahoe (3rd Generation GMT900)"),
    ],
    "chevrolet_tracker": [
        (1989, 1998, "Chevrolet Tracker (1st Generation JA)"),
        (1999, 2004, "Chevrolet Tracker (2nd Generation)"),
    ],
    "chevrolet_trailblazer":[(2002, 2009, "Chevrolet TrailBlazer (GMT360)")],
    "chevrolet_traverse":   [(2009, 2017, "Chevrolet Traverse (1st Generation Lambda)")],
    "chevrolet_uplander":   [(2005, 2009, "Chevrolet Uplander (U-body)")],
    "chevrolet_v10":       [(1960, 1987, "Chevrolet V10 4WD (C/K)")],
    "chevrolet_v20":       [(1960, 1987, "Chevrolet V20 4WD (C/K)")],
    "chevrolet_vega":      [(1971, 1977, "Chevrolet Vega (H-body)")],
    "chevrolet_venture":   [(1997, 2005, "Chevrolet Venture (U-body)")],
    "chevrolet_volt": [
        (2011, 2015, "Chevrolet Volt (1st Generation)"),
        (2016, 2019, "Chevrolet Volt (2nd Generation)"),
    ],
    "chevrolet_yukon": [
        (1992, 1999, "Chevrolet Tahoe/Yukon (1st Generation GMT410)"),
        (2000, 2006, "GMC Yukon (2nd Generation GMT800)"),
        (2007, 2014, "GMC Yukon (3rd Generation GMT900)"),
    ],
    # ── CHRYSLER ──────────────────────────────────────────────────────────────
    "chrysler_200": [
        (2011, 2014, "Chrysler 200 (1st Generation JS)"),
        (2015, 2017, "Chrysler 200 (2nd Generation UF)"),
    ],
    "chrysler_300": [
        (1955, 1965, "Chrysler 300 Letter Series"),
        (1979, 1983, "Chrysler 300 (M/R-body)"),
        (2005, 2010, "Chrysler 300 (LX)"),
        (2011, 2023, "Chrysler 300 (LX II)"),
    ],
    "chrysler_aspen":      [(2007, 2009, "Chrysler Aspen (DS)")],
    "chrysler_cirrus":     [(1995, 2000, "Chrysler Cirrus (JA)")],
    "chrysler_concorde": [
        (1993, 1997, "Chrysler Concorde (1st Generation LH)"),
        (1998, 2004, "Chrysler Concorde (2nd Generation LH)"),
    ],
    "chrysler_conquest":   [(1984, 1989, "Chrysler Conquest (1st Generation)")],
    "chrysler_cordoba":    [(1975, 1983, "Chrysler Cordoba (1st Generation)")],
    "chrysler_crossfire":  [(2004, 2008, "Chrysler Crossfire (1st Generation)")],
    "chrysler_fifth avenue":[(1979, 1993, "Chrysler Fifth Avenue (M/J/R-body)")],
    "chrysler_imperial": [
        (1926, 1975, "Chrysler Imperial"),
        (1981, 1983, "Chrysler Imperial (J-body)"),
        (1990, 1993, "Chrysler Imperial (Y-body)"),
    ],
    "chrysler_intrepid": [
        (1993, 1997, "Chrysler Intrepid (1st Generation LH)"),
        (1998, 2004, "Chrysler Intrepid (2nd Generation LH)"),
    ],
    "chrysler_lebaron": [
        (1977, 1981, "Chrysler LeBaron (M-body)"),
        (1982, 1995, "Chrysler LeBaron (K/J-body)"),
    ],
    "chrysler_lhs": [
        (1994, 1997, "Chrysler LHS (1st Generation LH)"),
        (1999, 2001, "Chrysler LHS (2nd Generation LH)"),
    ],
    "chrysler_new yorker": [(1940, 1996, "Chrysler New Yorker")],
    "chrysler_newport":    [(1961, 1981, "Chrysler Newport")],
    "chrysler_pacifica": [
        (2004, 2008, "Chrysler Pacifica (1st Generation CS)"),
        (2017, 2023, "Chrysler Pacifica (2nd Generation RU)"),
    ],
    "chrysler_pt cruiser": [(2001, 2010, "Chrysler PT Cruiser (PT)")],
    "chrysler_royal":      [(1937, 1959, "Chrysler Royal")],
    "chrysler_sebring": [
        (1995, 2000, "Chrysler Sebring (1st Generation JX)"),
        (2001, 2006, "Chrysler Sebring (2nd Generation JR)"),
        (2007, 2010, "Chrysler Sebring (3rd Generation JS)"),
    ],
    "chrysler_town&country": [
        (1990, 1995, "Chrysler Town & Country (1st Generation AS)"),
        (1996, 2000, "Chrysler Town & Country (2nd Generation GS)"),
        (2001, 2007, "Chrysler Town & Country (3rd Generation RS)"),
        (2008, 2016, "Chrysler Town & Country (4th Generation RT)"),
    ],
    "chrysler_voyager": [
        (1984, 1990, "Chrysler Voyager (1st Generation AS)"),
        (1991, 1995, "Chrysler Voyager (2nd Generation AS)"),
        (1996, 2000, "Chrysler Voyager (3rd Generation GS)"),
        (2001, 2007, "Chrysler Voyager (4th Generation RS)"),
    ],
    "chrysler_windsor":    [(1939, 1961, "Chrysler Windsor")],
    # ── DODGE ─────────────────────────────────────────────────────────────────
    "dodge_aspen":         [(1976, 1980, "Dodge Aspen (F-body)")],
    "dodge_attitude":      [(2006, 2012, "Dodge Attitude (1st Generation)")],
    "dodge_avenger": [
        (1995, 2000, "Dodge Avenger (1st Generation JA)"),
        (2008, 2014, "Dodge Avenger (2nd Generation JS)"),
    ],
    "dodge_caliber":       [(2007, 2012, "Dodge Caliber (PM)")],
    "dodge_challenger": [
        (1970, 1974, "Dodge Challenger (1st Generation E-body)"),
        (1978, 1983, "Dodge Challenger (2nd Generation)"),
        (2008, 2023, "Dodge Challenger (3rd Generation LC)"),
    ],
    "dodge_charger": [
        (1966, 1967, "Dodge Charger (1st Generation B-body)"),
        (1968, 1970, "Dodge Charger (2nd Generation B-body)"),
        (1971, 1974, "Dodge Charger (3rd Generation B-body)"),
        (1975, 1978, "Dodge Charger (4th Generation B-body)"),
        (2006, 2010, "Dodge Charger (6th Generation LX)"),
        (2011, 2023, "Dodge Charger (7th Generation LD)"),
    ],
    "dodge_colt":          [(1970, 1994, "Dodge Colt")],
    "dodge_coronet": [
        (1949, 1959, "Dodge Coronet (1st/2nd Generation)"),
        (1965, 1976, "Dodge Coronet (5th/6th Generation B-body)"),
    ],
    "dodge_cummins": [
        (1989, 2002, "Dodge Ram Cummins Diesel (1st/2nd Generation)"),
        (2003, 2018, "Dodge Ram Cummins Diesel (3rd/4th Generation)"),
    ],
    "dodge_d100": [
        (1961, 1971, "Dodge D-Series (2nd Generation)"),
        (1972, 1980, "Dodge D-Series (3rd Generation)"),
    ],
    "dodge_d150": [
        (1972, 1980, "Dodge D-Series (3rd Generation)"),
        (1981, 1993, "Dodge D-Series (4th Generation)"),
    ],
    "dodge_d200": [
        (1961, 1971, "Dodge D-Series (2nd Generation)"),
        (1972, 1980, "Dodge D-Series (3rd Generation)"),
    ],
    "dodge_d250": [
        (1972, 1980, "Dodge D-Series (3rd Generation)"),
        (1981, 1993, "Dodge D-Series (4th Generation)"),
    ],
    "dodge_d350":          [(1981, 1993, "Dodge D-Series (4th Generation)")],
    "dodge_dakota": [
        (1987, 1996, "Dodge Dakota (1st Generation)"),
        (1997, 2004, "Dodge Dakota (2nd Generation AN)"),
        (2005, 2011, "Dodge Dakota (3rd Generation ND)"),
    ],
    "dodge_dart": [
        (1960, 1976, "Dodge Dart (1st Generation)"),
        (2013, 2016, "Dodge Dart (2nd Generation PF)"),
    ],
    "dodge_daytona":       [(1984, 1993, "Dodge Daytona (K-body)")],
    "dodge_demon": [
        (1971, 1972, "Dodge Demon (A-body)"),
        (2018, 2023, "Dodge Challenger SRT Demon"),
    ],
    "dodge_durango": [
        (1998, 2003, "Dodge Durango (1st Generation DN)"),
        (2004, 2009, "Dodge Durango (2nd Generation HB)"),
        (2011, 2023, "Dodge Durango (3rd Generation WD)"),
    ],
    "dodge_dynasty":       [(1988, 1993, "Dodge Dynasty (C-body)")],
    "dodge_grand caravan": [
        (1984, 1990, "Dodge Grand Caravan (1st Generation S)"),
        (1991, 1995, "Dodge Grand Caravan (2nd Generation AS)"),
        (1996, 2000, "Dodge Grand Caravan (3rd Generation GS)"),
        (2001, 2007, "Dodge Grand Caravan (4th Generation RS)"),
        (2008, 2020, "Dodge Grand Caravan (5th Generation RT)"),
    ],
    "dodge_intrepid": [
        (1993, 1997, "Dodge Intrepid (1st Generation LH)"),
        (1998, 2004, "Dodge Intrepid (2nd Generation LH)"),
    ],
    "dodge_journey":       [(2009, 2020, "Dodge Journey (JC49)")],
    "dodge_magnum":        [(2005, 2008, "Dodge Magnum (LX)")],
    "dodge_monaco": [
        (1965, 1976, "Dodge Monaco (C-body)"),
        (1977, 1978, "Dodge Monaco (B-body)"),
    ],
    "dodge_neon": [
        (1995, 1999, "Dodge Neon (1st Generation PL)"),
        (2000, 2005, "Dodge Neon (2nd Generation PL)"),
    ],
    "dodge_nitro":         [(2007, 2012, "Dodge Nitro (KA)")],
    "dodge_polara":        [(1960, 1973, "Dodge Polara (C-body)")],
    "dodge_ram_1500": [
        (1981, 1993, "Dodge Ram 1500 (1st Generation D-Series)"),
        (1994, 2001, "Dodge Ram 1500 (2nd Generation BR/BE)"),
        (2002, 2008, "Dodge Ram 1500 (3rd Generation DR/DH)"),
        (2009, 2018, "Ram 1500 (4th Generation DS)"),
    ],
    "dodge_ram_2500": [
        (1981, 1993, "Dodge Ram 2500 (1st Generation D-Series)"),
        (1994, 2002, "Dodge Ram 2500 (2nd Generation BR/BE)"),
        (2003, 2009, "Dodge Ram 2500 (3rd Generation DR/DH)"),
        (2010, 2018, "Ram 2500 (4th Generation DJ)"),
    ],
    "dodge_ram_3500": [
        (1981, 1993, "Dodge Ram 3500 (1st Generation D-Series)"),
        (1994, 2002, "Dodge Ram 3500 (2nd Generation BR/BE)"),
        (2003, 2009, "Dodge Ram 3500 (3rd Generation DR/DH)"),
        (2010, 2018, "Ram 3500 (4th Generation D3)"),
    ],
    "dodge_ram_4500":      [(2008, 2018, "Ram 4500 (Chassis Cab)")],
    "dodge_ram_5500":      [(2008, 2018, "Ram 5500 (Chassis Cab)")],
    "dodge_ramcharger": [
        (1974, 1979, "Dodge Ramcharger (1st Generation AD)"),
        (1980, 1993, "Dodge Ramcharger (2nd Generation AD)"),
    ],
    "dodge_rumble bee":    [(2004, 2005, "Dodge Ram Rumble Bee")],
    "dodge_shadow":        [(1987, 1994, "Dodge Shadow (P-body)")],
    "dodge_spirit":        [(1989, 1995, "Dodge Spirit (AA-body)")],
    "dodge_stealth":       [(1991, 1996, "Dodge Stealth (Z16A)")],
    "dodge_stratus": [
        (1995, 2000, "Dodge Stratus (1st Generation JA)"),
        (2001, 2006, "Dodge Stratus (2nd Generation JR)"),
    ],
    "dodge_viper": [
        (1992, 2002, "Dodge Viper (1st Generation SR I)"),
        (2003, 2010, "Dodge Viper (2nd Generation SR II)"),
        (2013, 2017, "Dodge Viper (3rd Generation VX)"),
    ],
    "dodge_w100":          [(1961, 1980, "Dodge W-Series 4WD (2nd/3rd Generation)")],
    "dodge_w150":          [(1981, 1993, "Dodge W150 4WD (4th Generation)")],
    "dodge_w200":          [(1961, 1980, "Dodge W200 4WD (2nd/3rd Generation)")],
    "dodge_w250":          [(1981, 1993, "Dodge W250 4WD (4th Generation)")],
    "dodge_w350":          [(1981, 1993, "Dodge W350 4WD (4th Generation)")],
    # ── FORD ──────────────────────────────────────────────────────────────────
    "ford_aerostar":       [(1986, 1997, "Ford Aerostar (1st Generation)")],
    "ford_anglia":         [(1939, 1967, "Ford Anglia")],
    "ford_aspire":         [(1994, 1997, "Ford Aspire")],
    "ford_bronco": [
        (1966, 1977, "Ford Bronco (1st Generation)"),
        (1978, 1979, "Ford Bronco (2nd Generation)"),
        (1980, 1986, "Ford Bronco (3rd Generation)"),
        (1987, 1991, "Ford Bronco (4th Generation)"),
        (1992, 1996, "Ford Bronco (5th Generation)"),
    ],
    "ford_c-max":          [(2013, 2018, "Ford C-Max (2nd Generation)")],
    "ford_cabriolet":      [(1964, 1973, "Ford Cabriolet/Convertible")],
    "ford_contour":        [(1995, 2000, "Ford Contour (CDW27)")],
    "ford_coupe":          [(1932, 1953, "Ford Coupe (Classic)")],
    "ford_courier": [
        (1952, 1960, "Ford Courier (1st Generation)"),
        (1972, 1982, "Ford Courier (2nd Generation)"),
    ],
    "ford_crown victoria": [
        (1992, 1997, "Ford Crown Victoria (1st Generation)"),
        (1998, 2012, "Ford Crown Victoria (2nd Generation)"),
    ],
    "ford_deluxe":         [(1936, 1940, "Ford Deluxe")],
    "ford_e150": [
        (1961, 1967, "Ford Econoline (1st Generation)"),
        (1968, 1974, "Ford E-Series (2nd Generation)"),
        (1975, 1991, "Ford E-Series (3rd Generation)"),
        (1992, 2014, "Ford E-Series (4th Generation)"),
    ],
    "ford_e250": [
        (1961, 1967, "Ford Econoline (1st Generation)"),
        (1968, 1974, "Ford E-Series (2nd Generation)"),
        (1975, 1991, "Ford E-Series (3rd Generation)"),
        (1992, 2014, "Ford E-Series (4th Generation)"),
    ],
    "ford_e350": [
        (1968, 1974, "Ford E-Series (2nd Generation)"),
        (1975, 1991, "Ford E-Series (3rd Generation)"),
        (1992, 2014, "Ford E-Series (4th Generation)"),
    ],
    "ford_e450":           [(1992, 2014, "Ford E-Series (4th Generation)")],
    "ford_edge":           [(2007, 2014, "Ford Edge (1st Generation CD3)")],
    "ford_escape": [
        (2001, 2004, "Ford Escape (1st Generation CD2)"),
        (2005, 2012, "Ford Escape (2nd Generation CD3)"),
        (2013, 2019, "Ford Escape (3rd Generation TB3)"),
    ],
    "ford_escort": [
        (1981, 1990, "Ford Escort (1st Generation CE2/CE3)"),
        (1991, 1996, "Ford Escort (2nd Generation CE2/CE3)"),
        (1997, 2003, "Ford Escort (3rd Generation CDW27)"),
    ],
    "ford_escort_wagon": [
        (1981, 1990, "Ford Escort Wagon (1st Generation CE2/CE3)"),
        (1991, 1996, "Ford Escort Wagon (2nd Generation CE2/CE3)"),
    ],
    "ford_excursion":      [(2000, 2005, "Ford Excursion (1st Generation)")],
    "ford_expedition": [
        (1997, 2002, "Ford Expedition (1st Generation UN93)"),
        (2003, 2006, "Ford Expedition (2nd Generation U222)"),
        (2007, 2017, "Ford Expedition (3rd Generation U324)"),
    ],
    "ford_explorer": [
        (1991, 1994, "Ford Explorer (1st Generation UN46)"),
        (1995, 2001, "Ford Explorer (2nd Generation UN105)"),
        (2002, 2005, "Ford Explorer (3rd Generation UN152)"),
        (2006, 2010, "Ford Explorer (4th Generation UN150)"),
    ],
    "ford_f100": [
        (1953, 1956, "Ford F-100 (2nd Generation)"),
        (1957, 1960, "Ford F-100 (3rd Generation)"),
        (1961, 1966, "Ford F-100 (4th Generation)"),
        (1967, 1972, "Ford F-100 (5th Generation)"),
    ],
    "ford_f150": [
        (1975, 1979, "Ford F-150 (6th Generation)"),
        (1980, 1986, "Ford F-150 (7th Generation)"),
        (1987, 1991, "Ford F-150 (8th Generation)"),
        (1992, 1996, "Ford F-150 (9th Generation)"),
        (1997, 2003, "Ford F-150 (10th Generation)"),
        (2004, 2008, "Ford F-150 (11th Generation)"),
        (2009, 2014, "Ford F-150 (12th Generation)"),
    ],
    "ford_f250": [
        (1967, 1972, "Ford F-250 (5th Generation)"),
        (1973, 1979, "Ford F-250 (6th Generation)"),
        (1980, 1986, "Ford F-250 (7th Generation)"),
        (1987, 1997, "Ford F-250 (8th/9th Generation)"),
        (1999, 2007, "Ford F-250 Super Duty (1st Generation)"),
        (2008, 2016, "Ford F-250 Super Duty (2nd Generation)"),
    ],
    "ford_f350": [
        (1999, 2007, "Ford F-350 Super Duty (1st Generation)"),
        (2008, 2016, "Ford F-350 Super Duty (2nd Generation)"),
    ],
    "ford_f450":           [(1999, 2016, "Ford F-450 Super Duty")],
    "ford_fairlane": [
        (1955, 1956, "Ford Fairlane (1st Generation)"),
        (1957, 1959, "Ford Fairlane (2nd Generation)"),
        (1960, 1961, "Ford Fairlane (3rd Generation)"),
        (1962, 1963, "Ford Fairlane (4th Generation)"),
        (1966, 1970, "Ford Fairlane (5th Generation)"),
    ],
    "ford_falcon": [
        (1960, 1963, "Ford Falcon (1st Generation)"),
        (1964, 1965, "Ford Falcon (2nd Generation)"),
        (1966, 1970, "Ford Falcon (3rd/4th Generation)"),
    ],
    "ford_festiva":        [(1988, 1993, "Ford Festiva (1st Generation)")],
    "ford_fiesta": [
        (1978, 1980, "Ford Fiesta (1st Generation)"),
        (2011, 2019, "Ford Fiesta (6th Generation)"),
    ],
    "ford_five hundred":   [(2005, 2007, "Ford Five Hundred (D258)")],
    "ford_flex":           [(2009, 2019, "Ford Flex (1st Generation)")],
    "ford_focus": [
        (2000, 2004, "Ford Focus (1st Generation C170)"),
        (2005, 2011, "Ford Focus (2nd Generation C307)"),
        (2012, 2018, "Ford Focus (3rd Generation C346)"),
    ],
    "ford_freestar":       [(2004, 2007, "Ford Freestar (1st Generation)")],
    "ford_freestyle":      [(2005, 2007, "Ford Freestyle (D258)")],
    "ford_fusion": [
        (2006, 2009, "Ford Fusion (1st Generation CD338)"),
        (2010, 2012, "Ford Fusion (2nd Generation CD338)"),
        (2013, 2020, "Ford Fusion (3rd Generation CD391)"),
    ],
    "ford_galaxie": [
        (1959, 1960, "Ford Galaxie (1st Generation)"),
        (1961, 1964, "Ford Galaxie (2nd/3rd Generation)"),
        (1965, 1968, "Ford Galaxie (4th Generation)"),
        (1969, 1974, "Ford Galaxie (5th Generation)"),
    ],
    "ford_granada": [
        (1975, 1980, "Ford Granada (1st Generation)"),
        (1981, 1982, "Ford Granada (2nd Generation)"),
    ],
    "ford_grand torino":   [(1972, 1976, "Ford Gran Torino (3rd/4th Generation)")],
    "ford_lincoln":        [(1920, 1990, "Lincoln (Ford Division)")],
    "ford_maverick": [
        (1970, 1977, "Ford Maverick (1st Generation)"),
        (2022, 2024, "Ford Maverick (2nd Generation)"),
    ],
    "ford_mustang": [
        (1964, 1973, "Ford Mustang (1st Generation)"),
        (1974, 1978, "Ford Mustang II (2nd Generation)"),
        (1979, 1993, "Ford Mustang (3rd Generation Fox Body)"),
        (1994, 2004, "Ford Mustang (4th Generation SN95)"),
        (2005, 2014, "Ford Mustang (5th Generation S197)"),
    ],
    "ford_mustang_convertible": [
        (1964, 1973, "Ford Mustang Convertible (1st Generation)"),
        (1979, 1993, "Ford Mustang Convertible (3rd Generation Fox Body)"),
        (1994, 2004, "Ford Mustang Convertible (4th Generation SN95)"),
        (2005, 2014, "Ford Mustang Convertible (5th Generation S197)"),
    ],
    "ford_mustang_gt": [
        (1964, 1973, "Ford Mustang GT (1st Generation)"),
        (1979, 1993, "Ford Mustang GT (3rd Generation Fox Body)"),
        (1994, 2004, "Ford Mustang GT (4th Generation SN95)"),
        (2005, 2014, "Ford Mustang GT (5th Generation S197)"),
    ],
    "ford_mustang_gt_convertible": [
        (1994, 2004, "Ford Mustang GT Convertible (4th Generation SN95)"),
        (2005, 2014, "Ford Mustang GT Convertible (5th Generation S197)"),
    ],
    "ford_mustang_mach":   [(1969, 1970, "Ford Mustang Mach 1 (1st Generation)")],
    "ford_pinto":          [(1971, 1980, "Ford Pinto")],
    "ford_powerstroke": [
        (1994, 2003, "Ford Power Stroke 7.3L Diesel"),
        (2003, 2010, "Ford Power Stroke 6.0/6.4L Diesel"),
    ],
    "ford_probe": [
        (1988, 1992, "Ford Probe (1st Generation)"),
        (1993, 1997, "Ford Probe (2nd Generation)"),
    ],
    "ford_ranchero": [
        (1957, 1959, "Ford Ranchero (1st Generation)"),
        (1960, 1965, "Ford Ranchero (2nd/3rd Generation)"),
        (1966, 1971, "Ford Ranchero (4th Generation)"),
        (1972, 1979, "Ford Ranchero (5th Generation)"),
    ],
    "ford_ranger": [
        (1983, 1992, "Ford Ranger (1st Generation)"),
        (1993, 1997, "Ford Ranger (2nd Generation)"),
        (1998, 2011, "Ford Ranger (3rd Generation)"),
    ],
    "ford_rat rod":        [(1930, 1960, "Ford Rat Rod (Custom)")],
    "ford_roadster":       [(1932, 1934, "Ford Roadster (Classic)")],
    "ford_super deluxe":   [(1941, 1948, "Ford Super Deluxe")],
    "ford_super duty": [
        (1999, 2007, "Ford Super Duty (1st Generation)"),
        (2008, 2016, "Ford Super Duty (2nd Generation)"),
    ],
    "ford_t":              [(1908, 1927, "Ford Model T")],
    "ford_taurus": [
        (1986, 1991, "Ford Taurus (1st Generation)"),
        (1992, 1995, "Ford Taurus (2nd Generation)"),
        (1996, 1999, "Ford Taurus (3rd Generation)"),
        (2000, 2007, "Ford Taurus (4th Generation)"),
    ],
    "ford_taurus_wagon": [
        (1986, 1991, "Ford Taurus Wagon (1st Generation)"),
        (1992, 1995, "Ford Taurus Wagon (2nd Generation)"),
        (1996, 1999, "Ford Taurus Wagon (3rd Generation)"),
        (2000, 2005, "Ford Taurus Wagon (4th Generation)"),
    ],
    "ford_tempo":          [(1984, 1994, "Ford Tempo (BT52)")],
    "ford_thunderbird": [
        (1955, 1957, "Ford Thunderbird (1st Generation)"),
        (1958, 1960, "Ford Thunderbird (2nd Generation)"),
        (1961, 1963, "Ford Thunderbird (3rd Generation)"),
        (1964, 1966, "Ford Thunderbird (4th Generation)"),
        (1967, 1971, "Ford Thunderbird (5th Generation)"),
        (1972, 1976, "Ford Thunderbird (6th Generation)"),
        (1977, 1979, "Ford Thunderbird (7th Generation)"),
        (1980, 1982, "Ford Thunderbird (8th Generation)"),
        (1983, 1988, "Ford Thunderbird (9th Generation)"),
        (1989, 1997, "Ford Thunderbird (10th Generation)"),
        (2002, 2005, "Ford Thunderbird (11th Generation)"),
    ],
    "ford_transit": [
        (1965, 1978, "Ford Transit (1st Generation)"),
        (1978, 2000, "Ford Transit (2nd/3rd Generation)"),
        (2000, 2013, "Ford Transit (4th Generation)"),
    ],
    "ford_windstar": [
        (1995, 1998, "Ford Windstar (1st Generation)"),
        (1999, 2003, "Ford Windstar (2nd Generation)"),
    ],
    "ford_woody":          [(1929, 1951, "Ford Woody Wagon")],
    # ── GMC ───────────────────────────────────────────────────────────────────
    "gmc_acadia":          [(2007, 2016, "GMC Acadia (1st Generation GMT351)")],
    "gmc_c1000": [
        (1960, 1966, "GMC C1000 (1st Generation)"),
        (1967, 1972, "GMC C1000 (2nd Generation)"),
    ],
    "gmc_c1500": [
        (1967, 1972, "GMC C1500 (2nd Generation)"),
        (1973, 1987, "GMC C1500 (3rd Generation)"),
        (1988, 1998, "GMC C1500 (4th Generation)"),
    ],
    "gmc_c2500": [
        (1967, 1972, "GMC C2500 (2nd Generation)"),
        (1973, 1987, "GMC C2500 (3rd Generation)"),
        (1988, 2000, "GMC C2500 (4th Generation)"),
    ],
    "gmc_c3500": [
        (1967, 1972, "GMC C3500 (2nd Generation)"),
        (1973, 1987, "GMC C3500 (3rd Generation)"),
        (1988, 2000, "GMC C3500 (4th Generation)"),
    ],
    "gmc_c4500":           [(1990, 2009, "GMC C4500 (Medium Duty)")],
    "gmc_c5500":           [(1990, 2009, "GMC C5500 (Medium Duty)")],
    "gmc_c6500":           [(1990, 2009, "GMC C6500 (Medium Duty)")],
    "gmc_c7500":           [(1990, 2009, "GMC C7500 (Medium Duty)")],
    "gmc_caballero":       [(1978, 1987, "GMC Caballero")],
    "gmc_canyon": [
        (2004, 2012, "GMC Canyon (1st Generation GMT355)"),
        (2015, 2022, "GMC Canyon (2nd Generation K2XX)"),
    ],
    "gmc_denali": [
        (1998, 2006, "GMC Yukon Denali (GMT800)"),
        (2007, 2014, "GMC Yukon Denali (GMT900)"),
    ],
    "gmc_envoy": [
        (1998, 2001, "GMC Envoy (1st Generation)"),
        (2002, 2009, "GMC Envoy (2nd Generation GMT360)"),
    ],
    "gmc_jimmy": [
        (1970, 1991, "GMC Jimmy (1st/2nd Generation K5)"),
        (1992, 2005, "GMC Jimmy (S-body)"),
    ],
    "gmc_k10": [
        (1960, 1966, "GMC K10 (1st Generation)"),
        (1967, 1972, "GMC K10 (2nd Generation)"),
        (1973, 1987, "GMC K10 (3rd Generation)"),
    ],
    "gmc_k15": [
        (1967, 1972, "GMC K15 (2nd Generation)"),
        (1973, 1987, "GMC K15 (3rd Generation)"),
    ],
    "gmc_k1500": [
        (1988, 1999, "GMC K1500 (4th Generation)"),
        (1999, 2006, "GMC Sierra K1500 (1st Generation GMT800)"),
    ],
    "gmc_k20": [
        (1960, 1966, "GMC K20 (1st Generation)"),
        (1967, 1972, "GMC K20 (2nd Generation)"),
        (1973, 1987, "GMC K20 (3rd Generation)"),
    ],
    "gmc_k2500": [
        (1988, 2000, "GMC K2500 (4th Generation)"),
        (1999, 2006, "GMC Sierra K2500 (1st Generation GMT800)"),
    ],
    "gmc_k3500": [
        (1988, 2000, "GMC K3500 (4th Generation)"),
        (1999, 2006, "GMC Sierra K3500 (1st Generation GMT800)"),
    ],
    "gmc_safari": [
        (1985, 1994, "GMC Safari (1st Generation)"),
        (1995, 2005, "GMC Safari (2nd Generation)"),
    ],
    "gmc_savana":          [(1996, 2024, "GMC Savana (1st Generation)")],
    "gmc_savana_2500":     [(1996, 2024, "GMC Savana 2500 (1st Generation)")],
    "gmc_savana_3500":     [(1996, 2024, "GMC Savana 3500 (1st Generation)")],
    "gmc_sierra_1500": [
        (1999, 2006, "GMC Sierra 1500 (1st Generation GMT800)"),
        (2007, 2013, "GMC Sierra 1500 (2nd Generation GMT900)"),
        (2014, 2018, "GMC Sierra 1500 (3rd Generation K2XX)"),
    ],
    "gmc_sierra_2500": [
        (1999, 2006, "GMC Sierra 2500 (1st Generation GMT800)"),
        (2007, 2013, "GMC Sierra 2500 (2nd Generation GMT900)"),
        (2014, 2018, "GMC Sierra 2500 (3rd Generation K2XX)"),
    ],
    "gmc_sierra_3500": [
        (1999, 2006, "GMC Sierra 3500 (1st Generation GMT800)"),
        (2007, 2013, "GMC Sierra 3500 (2nd Generation GMT900)"),
        (2014, 2018, "GMC Sierra 3500 (3rd Generation K2XX)"),
    ],
    "gmc_sonoma": [
        (1982, 1993, "GMC Sonoma (1st Generation)"),
        (1994, 2004, "GMC Sonoma (2nd Generation)"),
    ],
    "gmc_suburban_1500": [
        (1992, 1999, "GMC Suburban 1500 (8th Generation GMT400)"),
        (2000, 2006, "GMC Suburban 1500 (9th Generation GMT800)"),
        (2007, 2014, "GMC Suburban 1500 (10th Generation GMT900)"),
    ],
    "gmc_suburban_2500": [
        (1992, 1999, "GMC Suburban 2500 (8th Generation GMT400)"),
        (2000, 2006, "GMC Suburban 2500 (9th Generation GMT800)"),
    ],
    "gmc_terrain":         [(2010, 2017, "GMC Terrain (1st Generation Theta+)")],
    "gmc_topkick":         [(1980, 2009, "GMC TopKick (Commercial)")],
    "gmc_vandura":         [(1964, 1995, "GMC Vandura (G-Series)")],
    "gmc_yukon_1500": [
        (1992, 1999, "GMC Yukon (1st Generation GMT410)"),
        (2000, 2006, "GMC Yukon (2nd Generation GMT800)"),
        (2007, 2014, "GMC Yukon (3rd Generation GMT900)"),
    ],
    "gmc_yukon_2500": [
        (1992, 1999, "GMC Yukon (1st Generation GMT410)"),
        (2000, 2006, "GMC Yukon 2500 (2nd Generation GMT800)"),
    ],
    # ── JEEP ──────────────────────────────────────────────────────────────────
    "jeep_cherokee": [
        (1974, 1983, "Jeep Cherokee (SJ)"),
        (1984, 2001, "Jeep Cherokee (XJ)"),
        (2014, 2023, "Jeep Cherokee (KL)"),
    ],
    "jeep_cj5":            [(1955, 1983, "Jeep CJ-5")],
    "jeep_cj7":            [(1976, 1986, "Jeep CJ-7")],
    "jeep_comanche":       [(1986, 1992, "Jeep Comanche (MJ)")],
    "jeep_commander": [
        (1984, 1991, "Jeep Commander (XJ-based)"),
        (2006, 2010, "Jeep Commander (XK)"),
    ],
    "jeep_compass":        [(2007, 2017, "Jeep Compass (1st Generation MK)")],
    "jeep_gladiator":      [(2020, 2024, "Jeep Gladiator (JT)")],
    "jeep_grand_cherokee": [
        (1993, 1998, "Jeep Grand Cherokee (ZJ)"),
        (1999, 2004, "Jeep Grand Cherokee (WJ)"),
        (2005, 2010, "Jeep Grand Cherokee (WK)"),
        (2011, 2021, "Jeep Grand Cherokee (WK2)"),
    ],
    "jeep_grand_wagoneer": [(1963, 1991, "Jeep Grand Wagoneer (SJ)")],
    "jeep_j10":            [(1970, 1988, "Jeep J-Series Pickup")],
    "jeep_j8":             [(1970, 1988, "Jeep J-Series Pickup")],
    "jeep_kaiser":         [(1963, 1968, "Kaiser-Jeep")],
    "jeep_liberty": [
        (2002, 2007, "Jeep Liberty (1st Generation KJ)"),
        (2008, 2012, "Jeep Liberty (2nd Generation KK)"),
    ],
    "jeep_patriot":        [(2007, 2017, "Jeep Patriot (MK)")],
    "jeep_renegade":       [(2015, 2024, "Jeep Renegade (1st Generation BU)")],
    "jeep_scrambler":      [(1981, 1985, "Jeep Scrambler (CJ-8)")],
    "jeep_wagoneer":       [(1963, 1991, "Jeep Wagoneer (SJ)")],
    "jeep_wrangler": [
        (1987, 1995, "Jeep Wrangler (YJ)"),
        (1997, 2006, "Jeep Wrangler (TJ)"),
        (2007, 2018, "Jeep Wrangler (JK)"),
    ],
    "jeep_wrangler_rubicon": [
        (2003, 2006, "Jeep Wrangler Rubicon (TJ)"),
        (2007, 2018, "Jeep Wrangler Rubicon (JK)"),
    ],
    "jeep_wrangler_sahara": [
        (1997, 2006, "Jeep Wrangler Sahara (TJ)"),
        (2007, 2018, "Jeep Wrangler Sahara (JK)"),
    ],
    "jeep_wrangler_tj":       [(1997, 2006, "Jeep Wrangler (TJ)")],
    "jeep_wrangler_unlimited": [
        (2004, 2006, "Jeep Wrangler Unlimited (TJ-LJ)"),
        (2007, 2018, "Jeep Wrangler Unlimited (JK)"),
    ],
    # ── LINCOLN ───────────────────────────────────────────────────────────────
    "lincoln_aviator":     [(2003, 2005, "Lincoln Aviator (1st Generation UN152)")],
    "lincoln_blackwood":   [(2002, 2002, "Lincoln Blackwood")],
    "lincoln_continental": [
        (1940, 1948, "Lincoln Continental (1st Generation)"),
        (1956, 1957, "Lincoln Continental Mark II (2nd Generation)"),
        (1958, 1960, "Lincoln Continental (3rd Generation)"),
        (1961, 1969, "Lincoln Continental (4th/5th Generation)"),
        (1970, 1979, "Lincoln Continental (6th Generation)"),
        (1980, 2002, "Lincoln Continental (7th-9th Generation)"),
    ],
    "lincoln_cosmopolitan": [(1948, 1954, "Lincoln Cosmopolitan")],
    "lincoln_limousine":    [(1965, 2011, "Lincoln Limousine (Town Car-based)")],
    "lincoln_ls":           [(2000, 2006, "Lincoln LS (1st Generation)")],
    "lincoln_mark_iii":     [(1968, 1971, "Lincoln Continental Mark III")],
    "lincoln_mark_iv":      [(1972, 1976, "Lincoln Continental Mark IV")],
    "lincoln_mark_lt":      [(2006, 2008, "Lincoln Mark LT")],
    "lincoln_mark_v":       [(1977, 1979, "Lincoln Continental Mark V")],
    "lincoln_mark_vi":      [(1980, 1983, "Lincoln Continental Mark VI")],
    "lincoln_mark_vii":     [(1984, 1992, "Lincoln Continental Mark VII")],
    "lincoln_mark_viii":    [(1993, 1998, "Lincoln Continental Mark VIII")],
    "lincoln_mks":          [(2009, 2019, "Lincoln MKS (1st Generation)")],
    "lincoln_mkt":          [(2010, 2019, "Lincoln MKT (1st Generation)")],
    "lincoln_mkx": [
        (2007, 2015, "Lincoln MKX (1st Generation CD3)"),
        (2016, 2018, "Lincoln MKX (2nd Generation)"),
    ],
    "lincoln_mkz": [
        (2006, 2012, "Lincoln MKZ (1st Generation CD338)"),
        (2013, 2020, "Lincoln MKZ (2nd Generation CD391)"),
    ],
    "lincoln_navigator": [
        (1998, 2002, "Lincoln Navigator (1st Generation UN93)"),
        (2003, 2006, "Lincoln Navigator (2nd Generation U222)"),
        (2007, 2017, "Lincoln Navigator (3rd Generation U324)"),
    ],
    "lincoln_premiere":    [(1956, 1960, "Lincoln Premiere")],
    "lincoln_towncar": [
        (1981, 1989, "Lincoln Town Car (1st Generation)"),
        (1990, 1997, "Lincoln Town Car (2nd Generation)"),
        (1998, 2011, "Lincoln Town Car (3rd Generation)"),
    ],
    "lincoln_zephyr": [
        (1936, 1948, "Lincoln Zephyr (Classic)"),
        (2006, 2006, "Lincoln Zephyr (MKZ)"),
    ],
    # ── MERCURY ───────────────────────────────────────────────────────────────
    "mercury_capri":       [(1979, 1986, "Mercury Capri (1st Generation)")],
    "mercury_comet":       [(1960, 1977, "Mercury Comet")],
    "mercury_cougar": [
        (1967, 1970, "Mercury Cougar (1st/2nd Generation)"),
        (1971, 1973, "Mercury Cougar (3rd Generation)"),
        (1974, 1976, "Mercury Cougar (4th Generation)"),
        (1999, 2002, "Mercury Cougar (5th Generation)"),
    ],
    "mercury_cyclone":     [(1968, 1971, "Mercury Cyclone (Fairlane-based)")],
    "mercury_grandmarquis": [
        (1983, 1991, "Mercury Grand Marquis (1st Generation)"),
        (1992, 2011, "Mercury Grand Marquis (2nd Generation)"),
    ],
    "mercury_marauder":    [(2003, 2004, "Mercury Marauder (1st Generation)")],
    "mercury_mariner":     [(2005, 2011, "Mercury Mariner (CD3)")],
    "mercury_milan":       [(2006, 2011, "Mercury Milan (CD338)")],
    "mercury_montclair":   [(1955, 1960, "Mercury Montclair")],
    "mercury_montego": [
        (1968, 1976, "Mercury Montego (Fairlane-based)"),
        (2005, 2007, "Mercury Montego (D258)"),
    ],
    "mercury_monterey": [
        (1952, 1974, "Mercury Monterey"),
        (2004, 2007, "Mercury Monterey (Minivan)"),
    ],
    "mercury_mountaineer": [
        (1997, 2001, "Mercury Mountaineer (1st Generation UN105)"),
        (2002, 2010, "Mercury Mountaineer (2nd Generation UN152)"),
    ],
    "mercury_mystique":    [(1995, 2000, "Mercury Mystique (CDW27)")],
    "mercury_parklane":    [(1958, 1960, "Mercury Park Lane")],
    "mercury_sable": [
        (1986, 1991, "Mercury Sable (1st Generation)"),
        (1992, 1995, "Mercury Sable (2nd Generation)"),
        (1996, 1999, "Mercury Sable (3rd Generation)"),
        (2000, 2005, "Mercury Sable (4th Generation)"),
        (2007, 2009, "Mercury Sable (5th Generation)"),
    ],
    "mercury_topaz":       [(1984, 1994, "Mercury Topaz (BT52)")],
    "mercury_tracer": [
        (1988, 1989, "Mercury Tracer (1st Generation)"),
        (1991, 1999, "Mercury Tracer (2nd Generation)"),
    ],
    "mercury_villager":    [(1993, 2002, "Mercury Villager (1st Generation)")],
    # ── OLDSMOBILE ────────────────────────────────────────────────────────────
    "oldsmobile_442": [
        (1964, 1971, "Oldsmobile 442 (A-body)"),
        (1972, 1980, "Oldsmobile 442 (Cutlass-based)"),
    ],
    "oldsmobile_achieva":  [(1992, 1998, "Oldsmobile Achieva (N-body)")],
    "oldsmobile_alero":    [(1999, 2004, "Oldsmobile Alero (N-body)")],
    "oldsmobile_aurora": [
        (1995, 1999, "Oldsmobile Aurora (1st Generation G-body)"),
        (2001, 2003, "Oldsmobile Aurora (2nd Generation)"),
    ],
    "oldsmobile_bravada": [
        (1991, 1994, "Oldsmobile Bravada (1st Generation)"),
        (1996, 2004, "Oldsmobile Bravada (2nd/3rd Generation)"),
    ],
    "oldsmobile_cutlass": [
        (1961, 1963, "Oldsmobile Cutlass (1st Generation F-85)"),
        (1964, 1972, "Oldsmobile Cutlass (A-body)"),
        (1973, 1977, "Oldsmobile Cutlass (A-body Colonnade)"),
        (1978, 1988, "Oldsmobile Cutlass Supreme (G-body)"),
        (1989, 1997, "Oldsmobile Cutlass Supreme (W-body)"),
    ],
    "oldsmobile_eightyeight": [(1949, 1999, "Oldsmobile 88 / Delta 88")],
    "oldsmobile_intrigue":    [(1998, 2002, "Oldsmobile Intrigue (W-body)")],
    "oldsmobile_ninetyeight": [(1941, 1996, "Oldsmobile 98")],
    "oldsmobile_omega": [
        (1973, 1975, "Oldsmobile Omega (X-body)"),
        (1980, 1984, "Oldsmobile Omega (X-body 2nd Generation)"),
    ],
    "oldsmobile_silhouette": [
        (1990, 1996, "Oldsmobile Silhouette (1st Generation U-body)"),
        (1997, 2004, "Oldsmobile Silhouette (2nd Generation)"),
    ],
    "oldsmobile_starfire":   [(1961, 1966, "Oldsmobile Starfire (1st Generation)")],
    "oldsmobile_toronado": [
        (1966, 1970, "Oldsmobile Toronado (1st Generation E-body)"),
        (1971, 1978, "Oldsmobile Toronado (2nd/3rd Generation)"),
        (1986, 1992, "Oldsmobile Toronado (4th/5th Generation E-body)"),
    ],
    # ── PLYMOUTH ──────────────────────────────────────────────────────────────
    "plymouth_acclaim":    [(1989, 1995, "Plymouth Acclaim (AA-body)")],
    "plymouth_barracuda": [
        (1964, 1966, "Plymouth Barracuda (1st Generation A-body)"),
        (1967, 1969, "Plymouth Barracuda (2nd Generation A-body)"),
        (1970, 1974, "Plymouth Barracuda (3rd Generation E-body)"),
    ],
    "plymouth_belvedere":  [(1951, 1970, "Plymouth Belvedere")],
    "plymouth_breeze":     [(1996, 2000, "Plymouth Breeze (JA-body)")],
    "plymouth_colt":       [(1970, 1994, "Plymouth Colt")],
    "plymouth_cranbrook":  [(1951, 1954, "Plymouth Cranbrook")],
    "plymouth_deluxe":     [(1933, 1942, "Plymouth Deluxe")],
    "plymouth_duster":     [(1970, 1976, "Plymouth Duster (A-body)")],
    "plymouth_fury": [
        (1956, 1959, "Plymouth Fury (1st Generation)"),
        (1960, 1964, "Plymouth Fury (2nd/3rd Generation)"),
        (1965, 1973, "Plymouth Fury (4th/5th Generation)"),
    ],
    "plymouth_gtx":        [(1967, 1971, "Plymouth GTX (B-body)")],
    "plymouth_horizon":    [(1978, 1990, "Plymouth Horizon (L-body)")],
    "plymouth_laser":      [(1990, 1994, "Plymouth Laser (DSM 1st Generation)")],
    "plymouth_neon": [
        (1995, 1999, "Plymouth Neon (1st Generation PL)"),
        (2000, 2001, "Plymouth Neon (2nd Generation PL)"),
    ],
    "plymouth_prowler":    [(1997, 2002, "Plymouth Prowler")],
    "plymouth_reliant":    [(1981, 1989, "Plymouth Reliant (K-body)")],
    "plymouth_roadrunner": [(1968, 1980, "Plymouth Road Runner (B-body)")],
    "plymouth_satellite":  [(1965, 1974, "Plymouth Satellite (B-body)")],
    "plymouth_savoy":      [(1951, 1964, "Plymouth Savoy")],
    "plymouth_scamp":      [(1971, 1980, "Plymouth Scamp (A-body)")],
    "plymouth_sundance":   [(1987, 1994, "Plymouth Sundance (P-body)")],
    "plymouth_trailduster":[(1974, 1981, "Plymouth Trail Duster")],
    "plymouth_valiant":    [(1960, 1976, "Plymouth Valiant (A-body)")],
    "plymouth_volare":     [(1976, 1980, "Plymouth Volare (F-body)")],
    "plymouth_voyager": [
        (1984, 1990, "Plymouth Voyager (1st Generation S-body)"),
        (1991, 1995, "Plymouth Voyager (2nd Generation AS)"),
        (1996, 2000, "Plymouth Voyager (3rd Generation GS)"),
    ],
    # ── PONTIAC ───────────────────────────────────────────────────────────────
    "pontiac_aztek":       [(2001, 2005, "Pontiac Aztek (1st Generation)")],
    "pontiac_bonneville": [
        (1957, 1958, "Pontiac Bonneville (1st Generation)"),
        (1959, 1964, "Pontiac Bonneville (2nd/3rd Generation)"),
        (1965, 1970, "Pontiac Bonneville (4th/5th Generation)"),
        (1971, 1976, "Pontiac Bonneville (6th Generation B-body)"),
        (1977, 1981, "Pontiac Bonneville (7th Generation B-body)"),
        (1992, 1999, "Pontiac Bonneville (8th Generation H-body)"),
        (2000, 2005, "Pontiac Bonneville (9th Generation H-body)"),
    ],
    "pontiac_catalina":    [(1950, 1981, "Pontiac Catalina (B-body)")],
    "pontiac_chieftain":   [(1949, 1958, "Pontiac Chieftain")],
    "pontiac_fiero":       [(1984, 1988, "Pontiac Fiero (P-body)")],
    "pontiac_firebird": [
        (1967, 1969, "Pontiac Firebird (1st Generation F-body)"),
        (1970, 1981, "Pontiac Firebird (2nd Generation F-body)"),
        (1982, 1992, "Pontiac Firebird (3rd Generation F-body)"),
        (1993, 2002, "Pontiac Firebird (4th Generation F-body)"),
    ],
    "pontiac_g39":         [(2007, 2008, "Pontiac G3")],   # mislabeled
    "pontiac_g5":          [(2007, 2010, "Pontiac G5 (Delta)")],
    "pontiac_g6":          [(2005, 2010, "Pontiac G6 (Epsilon)")],
    "pontiac_g8":          [(2008, 2009, "Pontiac G8 (VE/Zeta)")],
    "pontiac_grandam": [
        (1973, 1975, "Pontiac Grand Am (1st Generation A-body)"),
        (1978, 1980, "Pontiac Grand Am (2nd Generation A-body)"),
        (1985, 1991, "Pontiac Grand Am (4th Generation N-body)"),
        (1992, 1998, "Pontiac Grand Am (5th Generation N-body)"),
        (1999, 2005, "Pontiac Grand Am (6th Generation N-body)"),
    ],
    "pontiac_grandprix": [
        (1962, 1964, "Pontiac Grand Prix (1st Generation B-body)"),
        (1965, 1968, "Pontiac Grand Prix (2nd/3rd Generation B-body)"),
        (1969, 1972, "Pontiac Grand Prix (4th Generation A-body)"),
        (1973, 1977, "Pontiac Grand Prix (5th Generation A-body)"),
        (1978, 1987, "Pontiac Grand Prix (6th Generation G-body)"),
        (1988, 1996, "Pontiac Grand Prix (7th Generation W-body)"),
        (1997, 2008, "Pontiac Grand Prix (8th Generation W-body)"),
    ],
    "pontiac_grandville":  [(1971, 1975, "Pontiac Grandville (B-body)")],
    "pontiac_gto": [
        (1964, 1967, "Pontiac GTO (1st Generation A-body)"),
        (1968, 1972, "Pontiac GTO (2nd Generation A-body)"),
        (1974, 1974, "Pontiac GTO (3rd Generation A-body)"),
        (2004, 2006, "Pontiac GTO (4th Generation)"),
    ],
    "pontiac_lemans": [
        (1961, 1963, "Pontiac LeMans (1st Generation)"),
        (1964, 1967, "Pontiac LeMans (A-body)"),
        (1968, 1973, "Pontiac LeMans (A-body 2nd Generation)"),
        (1974, 1981, "Pontiac LeMans (A-body 3rd Generation)"),
    ],
    "pontiac_montana": [
        (1999, 2004, "Pontiac Montana (1st Generation U-body)"),
        (2005, 2009, "Pontiac Montana SV6 (2nd Generation)"),
    ],
    "pontiac_parisienne":  [(1958, 1986, "Pontiac Parisienne")],
    "pontiac_pursuit":     [(2005, 2006, "Pontiac Pursuit (Delta)")],
    "pontiac_solstice":    [(2006, 2010, "Pontiac Solstice (Kappa)")],
    "pontiac_starchief":   [(1954, 1966, "Pontiac Star Chief (B-body)")],
    "pontiac_sunbird": [
        (1976, 1980, "Pontiac Sunbird (H-body)"),
        (1982, 1994, "Pontiac Sunbird (J-body)"),
    ],
    "pontiac_sunfire":     [(1995, 2005, "Pontiac Sunfire (J-body)")],
    "pontiac_tempest": [
        (1961, 1963, "Pontiac Tempest (1st Generation Y-body)"),
        (1964, 1970, "Pontiac Tempest (A-body)"),
    ],
    "pontiac_torrent":     [(2006, 2009, "Pontiac Torrent (Theta)")],
    "pontiac_transam": [
        (1969, 1981, "Pontiac Trans Am (2nd Generation F-body)"),
        (1982, 1992, "Pontiac Trans Am (3rd Generation F-body)"),
        (1993, 2002, "Pontiac Trans Am (4th Generation F-body)"),
    ],
    "pontiac_ventura": [
        (1960, 1963, "Pontiac Ventura (B-body)"),
        (1971, 1977, "Pontiac Ventura (X-body)"),
    ],
    "pontiac_vibe": [
        (2003, 2008, "Pontiac Vibe (1st Generation E130)"),
        (2009, 2010, "Pontiac Vibe (2nd Generation E140)"),
    ],
    "pontiac_wave":        [(2005, 2008, "Pontiac Wave (T200)")],
    # ── RAM ───────────────────────────────────────────────────────────────────
    "ram_1500": [
        (2009, 2012, "Ram 1500 (4th Generation DS)"),
        (2013, 2018, "Ram 1500 (4th Generation DS)"),
        (2019, 2023, "Ram 1500 (5th Generation DT)"),
    ],
    "ram_2500": [
        (2010, 2018, "Ram 2500 (4th Generation DJ)"),
        (2019, 2023, "Ram 2500 (5th Generation)"),
    ],
    "ram_3500": [
        (2010, 2018, "Ram 3500 (4th Generation D3)"),
        (2019, 2023, "Ram 3500 (5th Generation)"),
    ],
    # ── RAMBLER ───────────────────────────────────────────────────────────────
    "rambler_american":    [(1958, 1969, "Rambler American")],
    "rambler_rogue":       [(1967, 1969, "Rambler Rogue")],
    # ── SATURN ────────────────────────────────────────────────────────────────
    "saturn_astra":        [(2008, 2009, "Saturn Astra (J400)")],
    "saturn_aura":         [(2007, 2010, "Saturn Aura (Epsilon)")],
    "saturn_ion":          [(2003, 2007, "Saturn Ion (Delta)")],
    "saturn_l100":         [(2000, 2005, "Saturn L-Series (L-body)")],
    "saturn_l200":         [(2000, 2005, "Saturn L-Series (L-body)")],
    "saturn_l300":         [(2000, 2005, "Saturn L-Series (L-body)")],
    "saturn_ls":           [(2000, 2004, "Saturn LS (L-body)")],
    "saturn_lw200":        [(2000, 2005, "Saturn LW Wagon (L-body)")],
    "saturn_lw300":        [(2000, 2005, "Saturn LW Wagon (L-body)")],
    "saturn_outlook":      [(2007, 2010, "Saturn Outlook (GMT351)")],
    "saturn_relay":        [(2005, 2007, "Saturn Relay (U-body)")],
    "saturn_sc1":          [(1991, 2002, "Saturn SC (Z-body)")],
    "saturn_sc2":          [(1991, 2002, "Saturn SC (Z-body)")],
    "saturn_sky":          [(2007, 2010, "Saturn Sky (Kappa)")],
    "saturn_sl":           [(1991, 2002, "Saturn SL (Z-body)")],
    "saturn_sl1":          [(1991, 2002, "Saturn SL1 (Z-body)")],
    "saturn_sl2":          [(1991, 2002, "Saturn SL2 (Z-body)")],
    "saturn_sl2_wagon":    [(1991, 2001, "Saturn SW (Z-body)")],
    "saturn_sw2":          [(1991, 2001, "Saturn SW2 (Z-body)")],
    "saturn_view":         [(2002, 2007, "Saturn Vue (1st Generation)")],
    "saturn_vue": [
        (2002, 2007, "Saturn Vue (1st Generation)"),
        (2008, 2010, "Saturn Vue (2nd Generation Theta)"),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# MISC MAKES  (one-offs not covered above)
# ─────────────────────────────────────────────────────────────────────────────
MISC_MAP = {
    "am general_hummer":    [(1992, 2006, "AM General Hummer H1")],
    "am general_hummer_h1": [(1992, 2006, "AM General Hummer H1")],
    "am general_jeep_dj-5": [(1965, 1984, "AM General DJ-5")],
    "blakely_bearcat":      [(1972, 1978, "Blakely Bearcat")],
    "bradley_gt":           [(1971, 1981, "Bradley GT")],
    "can am_outlander":     [(2003, 2023, "Can-Am Outlander")],
    "can am_spyder":        [(2007, 2023, "Can-Am Spyder")],
    "daihatsu_rocky":       [(1984, 1998, "Daihatsu Rocky")],
    "daihatsu_yrv":         [(2000, 2005, "Daihatsu YRV")],
    "datsun_240z":          [(1969, 1973, "Datsun 240Z (S30)")],
    "datsun_260z":          [(1973, 1975, "Datsun 260Z (S30)")],
    "datsun_280z":          [(1975, 1978, "Datsun 280Z (S30)")],
    "datsun_b210":          [(1973, 1978, "Datsun B210")],
    "datsun_nissan":        [(1982, 1984, "Datsun/Nissan")],
    "daewoo_lanos":         [(1997, 2002, "Daewoo Lanos")],
    "daewoo_leganza":       [(1997, 2002, "Daewoo Leganza")],
    "daewoo_nubira":        [(1997, 2003, "Daewoo Nubira")],
    "mg_mgb":               [(1962, 1980, "MG MGB")],
    "mg_mgb_mk2":           [(1962, 1980, "MG MGB")],
    "mg_mgb_mk5":           [(1962, 1980, "MG MGB")],
    "mg_midget":            [(1961, 1979, "MG Midget")],
    "morris_minor":         [(1948, 1971, "Morris Minor")],
    "nash_metropolitan":    [(1954, 1961, "Nash Metropolitan")],
    "packard_super8":       [(1935, 1950, "Packard Super Eight")],
    "polaris_slingshot":    [(2015, 2023, "Polaris Slingshot")],
    "renault_captur":       [(2013, 2023, "Renault Captur (1st Generation)")],
    "studebaker_champion":  [(1939, 1958, "Studebaker Champion")],
    "studebaker_commander": [(1927, 1954, "Studebaker Commander")],
    "studebaker_flatbed":   [(1940, 1964, "Studebaker Flatbed Truck")],
    "studebaker_lark":      [(1959, 1966, "Studebaker Lark")],
    "sunbeam_rapier":       [(1955, 1976, "Sunbeam Rapier")],
    "tesla_s":              [(2012, 2023, "Tesla Model S (1st Generation)")],
    "triumph_gt6":          [(1966, 1973, "Triumph GT6")],
    "triumph_spitfire":     [(1962, 1980, "Triumph Spitfire")],
    "triumph_tr":           [(1953, 1981, "Triumph TR")],
    "triumph_vitesse":      [(1962, 1971, "Triumph Vitesse")],
    "willys_cj2a":          [(1945, 1949, "Willys CJ-2A")],
    "willys_cj3b":          [(1953, 1968, "Willys CJ-3B")],
    "hummer_h1":            [(1992, 2006, "Hummer H1")],
    "hummer_h2":            [(2002, 2009, "Hummer H2")],
    "hummer_h3":            [(2005, 2010, "Hummer H3")],
    "eagle_talon":          [
        (1990, 1994, "Eagle Talon (1st Generation)"),
        (1995, 1998, "Eagle Talon (2nd Generation)"),
    ],
    "subaru_360":           [(1958, 1971, "Subaru 360")],
    "subaru_brat":          [(1977, 1994, "Subaru BRAT")],
    "subaru_gl10":          [(1985, 1989, "Subaru GL10")],
    "subaru_svx":           [(1991, 1997, "Subaru SVX")],
}

# ─────────────────────────────────────────────────────────────────────────────
# MASTER LOOKUP — searched in order
# ─────────────────────────────────────────────────────────────────────────────
ALL_MAPS = [BMW_MAP, MERCEDES_MAP, EUROPEAN_MAP, JAPANESE_MAP, AMERICAN_MAP, MISC_MAP]


def lookup(make_model: str, year: int) -> str | None:
    for m in ALL_MAPS:
        if make_model in m:
            for (y0, y1, label) in m[make_model]:
                if y0 <= year <= y1:
                    return label
            # key exists but no range matched — return last label as fallback
            return m[make_model][-1][2]
    return None


def build_map(dirs_path: str, output_path: str, unmapped_path: str) -> None:
    with open(dirs_path, encoding="utf-8-sig") as f:
        dirs = [l.strip() for l in f if l.strip() and not l.strip().startswith(".")]

    result = {}
    unmapped = []

    for d in dirs:
        m = re.match(r"^(.+)_(\d{4})$", d)
        if not m:
            unmapped.append(f"{d}  [could not parse year]")
            continue
        make_model, year = m.group(1), int(m.group(2))
        label = lookup(make_model, year)
        if label:
            result[d] = label
        else:
            unmapped.append(f"{d}  [make_model={make_model!r}]")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    with open(unmapped_path, "w", encoding="utf-8") as f:
        f.write("\n".join(unmapped))

    print(f"Mapped:   {len(result)}")
    print(f"Unmapped: {len(unmapped)}")
    print(f"Output:   {output_path}")
    print(f"Unmapped: {unmapped_path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    dirs_file = os.path.join(base, "VMMRdb_dirs.txt")
    # regenerate dir list if not present
    if not os.path.exists(dirs_file):
        import subprocess
        entries = os.listdir(os.path.join(base, "VMMRdb"))
        with open(dirs_file, "w") as f:
            f.write("\n".join(entries))

    build_map(
        dirs_path=dirs_file,
        output_path=os.path.join(base, "generation_map.json"),
        unmapped_path=os.path.join(base, "generation_map_unmapped.txt"),
    )

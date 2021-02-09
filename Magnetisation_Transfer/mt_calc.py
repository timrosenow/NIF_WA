"""
Tool to calculate magnetic transfer saturation image from Bruker MRI scans.

Assumes you have MRtrix and nanconvert_bruker installed, and in the $PATH.
PvDataset should already be extracted. Run --help to see usage.

Args:
    singlecho: Single echo sequences, no averaging needed
    t1_file: 2dseq file for T1 weighted scan
    pd_file: 2dseq file for proton density scan
    mt_file: 2dseq file for MT scan
    save_file: File to save the output image

    nocleanup: Do not remove temporary files
    gauss: Apply a gaussian filter of nxnxn (default=0 i.e. no filter)
    at1: Flip angle of T1 scan (default=20)
    apd: Flip angle of PD scan (default=6)
    amt: Flip angle of MT scan (default=6)
    TRt1: TR for T1 scan in ms (default=18)
    TRpd: TR for PD scan in ms (default=25)
    TRmt: TR for MT scan in ms (default=25)
"""

import argparse
import os
import tempfile
import subprocess
from pathlib import Path

# Set up the arguments
parser = argparse.ArgumentParser(description="Calculate MT saturation image. Output to any MRtrix3 compatible format.")
parser.add_argument("t1_file", help="T1 scan (2dseq file)")
parser.add_argument("pd_file", help="PD scan (2dseq file)")
parser.add_argument("mt_file", help="MT scan (2dseq file)")
parser.add_argument("save_file", help="output file name (must end in appropriate file extension")
parser.add_argument("--singleecho", help="single echo scans performed", action="store_true")
parser.add_argument("--nocleanup", help="do not remove temporary folder", action="store_true")
parser.add_argument("--gauss", type=int, help="Apply a gaussian filter of NxNxN (default=0=NO FILTER)", default=0)
parser.add_argument("--at1", type=int, help="T1 scan flip angle (default 20)", default=20)
parser.add_argument("--apd", type=int, help="PD scan flip angle (default 6)", default=6)
parser.add_argument("--amt", type=int, help="MT scan flip angle (default 6)", default=6)
parser.add_argument("--TRt1", type=int, help="T1 scan TR (default 18)", default=18)
parser.add_argument("--TRpd", type=int, help="PD scan TR (default 25)", default=25)
parser.add_argument("--TRmt", type=int, help="MT scan TR (default 25)", default=25)
args = parser.parse_args()

# First create a working directory
tempfile.tempdir = '.'
tempdir = tempfile.mkdtemp()

# First convert all of the relevant scans to MIH format
# We shall henceforth refer to the scan files as t1, pd, and mt.
t1 = f"{tempdir}/t1_converted.nii"
pd = f"{tempdir}/pd_converted.nii"
mt = f"{tempdir}/mt_converted.nii"

subprocess.run(["nanconvert_bruker", args.t1_file, t1])
subprocess.run(["nanconvert_bruker", args.pd_file, pd])
subprocess.run(["nanconvert_bruker", args.mt_file, mt])

# If a multiecho sequence was run, average the file across the echoes to produce a single image
if not args.singleecho:
    subprocess.run(["mrmath", t1, "mean", f"{tempdir}/t1_avg.nii", "-axis", "3"])
    t1 = f"{tempdir}/t1_avg.nii"
    subprocess.run(["mrmath", pd, "mean", f"{tempdir}/pd_avg.nii", "-axis", "3"])
    pd = f"{tempdir}/pd_avg.nii"
    subprocess.run(["mrmath", mt, "mean", f"{tempdir}/mt_avg.nii", "-axis", "3"])
    mt = f"{tempdir}/mt_avg.nii"

# Apply a gaussian filter, if --gauss argument is provided and > 0
gauss = args.gauss
if gauss > 0:
    subprocess.run(["mrfilter", t1, "smooth", f"{tempdir}/t1_filtered.nii", "-extent", gauss])
    t1 = f"{tempdir}/t1_filtered.nii"
    subprocess.run(["mrfilter", pd, "smooth", f"{tempdir}/pd_filtered.nii", "-extent", gauss])
    pd = f"{tempdir}/pd_filtered.nii"
    subprocess.run(["mrfilter", mt, "smooth", f"{tempdir}/mt_filtered.nii", "-extent", gauss])
    mt = f"{tempdir}/mt_filtered.nii"

# The analysis is based on the Hagiwara 2018 paper (which is based on Helms 2008)
# For simplicity of typing, we will rename some of these variables
at1 = args.at1
apd = args.apd
amt = args.amt
TRt1 = args.TRt1
TRpd = args.TRpd
TRmt = args.TRmt

# First calculate R1 by splitting into two terms:
# R1 = (at1/TRt1) x t1 - (apd/TRpd) x pd
# R2 = (pd/aPD) - (t1/at1)
# R = 0.5 x R1 / R2
R1 = f"{tempdir}/R1.nii"
R2 = f"{tempdir}/R2.nii"
R = f"{tempdir}/R.nii"
subprocess.run(["mrcalc", t1, f"{at1 / TRt1}", "-mult", f"{apd / TRpd}", pd, "-mult", "-sub", R1])
subprocess.run(["mrcalc", pd, f"{apd}", "-div", t1, f"{at1}", "-div", "-sub", R2])
subprocess.run(["mrcalc", R1, R2, "-div", "2", "-div", R])

# Now calculate A by splitting into two terms:
# A1 = pd x t1 x ( (TRpd x at1 / apd) - (TRt1 x apd / at1))
# A2 = TRpd x at1 x t1 - TRt1 x apd x pd
# A = A1 / A2
A1 = f"{tempdir}/A1.nii"
A2 = f"{tempdir}/A2.nii"
A = f"{tempdir}/A.nii"
subprocess.run(["mrcalc", pd, t1, "-mult", f"{(TRpd * at1 / apd) - (TRt1 * apd / at1)}", "-mult", A1])
subprocess.run(["mrcalc", t1, f"{TRpd * at1}", "-mult", pd, f"{TRt1 * apd}", "-mult", "-sub", A2])
subprocess.run(["mrcalc", A1, A2, "-div", A])

# Finally, calculate MTsat, by splitting into three terms:
# M1 = (amt x A / mt) - 1
# M2 = TRmt x R
# M3 = amt x amt / 2 (numeric constant)
# MTsat = M1 x M2 - M3
M1 = f"{tempdir}/M1.nii"
M2 = f"{tempdir}/M2.nii"
M3 = amt * amt / 2

subprocess.run(["mrcalc", A, f"{amt}", "-mult", mt, "-div", "1", "-sub", M1])
subprocess.run(["mrcalc", f"{TRmt}", R, "-mult", M2])
subprocess.run(["mrcalc", M1, M2, "-mult", f"{M3}", "-sub", args.save_file])

# Delete the temporary files, unless --nocleanup specified
if args.nocleanup:
    print(f"Attempting to remove temporary directory {tempdir}")
    subprocess.run(["rm", "-r", "-I", f"{tempdir}"])

exit()

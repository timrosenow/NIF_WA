"""
Tool to create basic DTI metrics from a Bruker 2dseq file.

Calculates fractional anisotropy (FA) map, radial diffusivity (RD) map,
apparent diffusion coefficient (ADC) map, and extracts the B0 image. Saves
as any MRtrix format, defaults to .nii.

Assumes you have MRtrix and nanconvert_bruker installed, and in the $PATH.
PvDataset should already be extracted. Run --help to see usage.

Args:
    scan_file: location of the 2dseq file of the raw DTI scan (not the reconstruction)
    fa_file: file to save the FA map (default fa_map.nii)
    rd_file: file to save the RD map (default rd_map.nii)
    adc_file: file to save the ADC map (default adc_map.nii)
    b0_file: file to save the B0 image (default b0_image.nii)
"""

import argparse
import subprocess
import tempfile

# Set up the arguments
parser = argparse.ArgumentParser(description="Calculate basic DTI metrics and output to any MRtrix3 compatible format.")
parser.add_argument("scan_file", help="DTI scan raw data (2dseq file), NOT the reconstruction")
parser.add_argument("--fa_file", help="Filename for FA map output (default fa_map.nii)", default="fa_map.nii")
parser.add_argument("--rd_file", help="Filename for RD map output (default rd_map.nii)", default="rd_map.nii")
parser.add_argument("--adc_file", help="Filename for ADC map output (default adc_map.nii)", default="adc_map.nii")
parser.add_argument("--b0_file", help="Filename for B0 image output (default b0_image.nii)", default="b0_image.nii")
args = parser.parse_args()

# Create a temporary folder for working with scans
tempfile.tempdir = '.'
tempdir = tempfile.mkdtemp()

# Create an MRtrix file with appropriate B vectors
subprocess.run(["nanconvert_bruker", args.scan_file, f"{tempdir}/dti_scan.nii"])

# Replace small vector gradient magnitudes with 0 (to account for slice select gradient).
# Note that this is often around 300, so replace anything less than 500 with 0.
# Achieved with a complex awk command because I'm too lazy to do it in python.
awk_cmd = '{ for (i = 1; i <= NF; i++) if ($i < 500) $i = 0; print}'
subprocess.run(["awk", "-i", "inplace", awk_cmd, f"{tempdir}/dti_scan.bval"])

# Now convert the .nii file to MRtrix, with the B vectors/values embedded
subprocess.run(["mrconvert", "-fslgrad", f"{tempdir}/dti_scan.bvec", f"{tempdir}/dti_scan.bval",
                f"{tempdir}/dti_scan.nii", f"{tempdir}/dti_scan.mih"])

# And create a tensor file too
subprocess.run(["dwi2tensor", f"{tempdir}/dti_scan.mih", f"{tempdir}/dti_tensor.mih"])

# Now reconstruct the DTI metrics
subprocess.run(["tensor2metric", "-fa", args.fa_file, "-rd", args.rd_file, "-adc", args.adc_file,
                f"{tempdir}/dti_tensor.mih"])

# Now create a B0 image from the

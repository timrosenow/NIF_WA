#!/usr/bin/python3

"""
Tool to generate basic MRI metrics (ADC, RD, FA map, and a B0 image) from
a Bruker file.

Assumes you have MRtrix and nanconvert_bruker installed, and in the $PATH.
PvDataset should already be extracted. Run --help to see usage.

Args:
	save_file: File to save the output image
	singlecho: Single echo sequences, no averaging needed

	t1: 2dseq file for T1 weighted scan
	pd: 2dseq file for proton density scan
	mt: 2dseq file for MT scan

	at1: Flip angle of T1 scan (default=20)
	apd: Flip angle of PD scan (default=6)
	amt: Flip angle of MT scan (default=6)
	TRt1: TR for T1 scan in ms (default=18)
	TRpd: TR for PD scan in ms (default=25)
	TRmt: TR for MT scan in ms (default=25)

"""
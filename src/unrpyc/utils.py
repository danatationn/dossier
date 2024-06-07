''' THIS FILE IS NOT INCLUDED IN THE UNRPYC MODULE BUT DOES REUSE UNRPYC CODE '''

from pathlib import Path
from .. import log
import struct, zlib

from src.unrpyc import decompiler
from src.unrpyc.decompiler import astdump, translate
from src.unrpyc.decompiler.renpycompat import (pickle_safe_loads, pickle_safe_dumps, pickle_safe_dump, pickle_loads, pickle_detect_python2)


def read_ast_from_file(in_file):
	# Reads rpyc v1 or v2 file
	# v1 files are just a zlib compressed pickle blob containing some data and the ast
	# v2 files contain a basic archive structure that can be parsed to find the same blob
	raw_contents = in_file.read()
	file_start = raw_contents[:50]
	is_rpyc_v1 = False

	if not raw_contents.startswith(b"RENPY RPC2"):
		# if the header isn't present, it should be a RPYC V1 file, which is just the blob
		contents = raw_contents
		is_rpyc_v1 = True

	else:
		# parse the archive structure
		position = 10
		chunks = {}
		have_errored = False

		for expected_slot in range(1, 0xFFFFFFFF):
			slot, start, length = struct.unpack("III", raw_contents[position: position + 12])

			if slot == 0:
				break

			if slot != expected_slot and not have_errored:
				have_errored = True

				log.warn(
					"Warning: Encountered an unexpected slot structure. It is possible the \n"
					"    file header structure has been changed.")

			position += 12

			chunks[slot] = raw_contents[start: start + length]

		if 1 not in chunks:
			# context.set_state('bad_header')
			raise Exception(
				"Unable to find the right slot to load from the rpyc file. The file header "
				f"structure has been changed. File header: {file_start}")

		contents = chunks[1]

	try:
		contents = zlib.decompress(contents)
	except Exception:
		context.set_state('bad_header')
		raise Exception(
			"Did not find a zlib compressed blob where it was expected. Either the header has been "
			f"modified or the file structure has been changed. File header: {file_start}") from None

	# add some detection of ren'py 7 files
	if is_rpyc_v1 or pickle_detect_python2(contents):
		version = "6" if is_rpyc_v1 else "7"

		log.warn(
			"Warning: analysis found signs that this .rpyc file was generated by ren'py \n"
		   f'    version {version} or below, while this unrpyc version targets ren\'py \n'
			"    version 8. Decompilation will still be attempted, but errors or incorrect \n"
			"    decompilation might occur. ")

	_, stmts = pickle_safe_loads(contents)
	return stmts

def decompile_rpyc(file_path: Path) -> None:
	if not file_path.suffix == '.rpyc':
		log.debug(f'Skipping {file_path.name}... (isn\'t .rpyc)')
		return
	
	decomp_path = file_path.with_suffix('.rpy')
	if decomp_path.exists():
		log.debug(f'Skipping {file_path.name}... (file already exists)')
		return

	with open(file_path, 'rb') as f:
		ast = read_ast_from_file(f)

	with open(decomp_path, 'w', encoding='utf-8') as f:
		astdump.pprint(f, ast)
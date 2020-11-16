from pymmax2.pyMMAX2 import *
import sys, argparse, nltk, ntpath
from glob import glob

parser = argparse.ArgumentParser()
source = parser.add_mutually_exclusive_group(required=True)
# For processing a single file
source.add_argument('--mmax_file', default=None)
# For processing all .mmax files in mmax_dir
source.add_argument('--mmax_dir', default=None)
parser.add_argument('--common_paths', required=False,  default="")
args=parser.parse_args()

if args.mmax_dir:
	files = [f for f in glob(args.mmax_dir+'**', recursive=True) if f.endswith(".mmax")]
else:
	files = [args.mmax_file]

for f in files:
	# Open w/o deep access to annotation scheme first
	pd = MMAX2Discourse(f, common_paths=args.common_paths, verbose=True)
	pd.load_markables()

	# Create new level.
	# This is only executed for the first .mmax file that is processed in [files].
	# It will create a new entry in the current common_paths file.
	# For subsequent files, the pos level already exists in common_paths (though it will be empty, 
	# and lacking a namespace, which will be set explicitly below!)
	pos_namespace='xmlns="www.pymmax2.org/NameSpaces/pos"'
	try:
		pos_level=pd.add_markablelevel("pos", namespace=pos_namespace, dtd_path='"markables.dtd"', create_if_missing=True)
		# full=True means including the .mmax file, which is what we want here
		# Set filename to placeholder version for common_paths file
		pos_level.set_filename(ntpath.basename(pd.get_mmax2_project().get_mmax2_path(full=False))+"$_pos_level.xml")
		# Write commonpaths file (this will also create a backup)
		# With the next iteration if [files], the pos level will be available
		pd.get_commonpaths().write(overwrite=True)
		# Set filename to actual name, using the project name
		pos_level.set_filename(ntpath.basename(pd.get_mmax2_project().get_mmax2_path(full=True))[0:-5]+"_pos_level.xml")
		# Create scheme and customization placeholders to make project formally complete.
		pd.get_commonpaths().write_scheme_stub(for_levelname="pos")
		pd.get_commonpaths().write_customization_stub(for_levelname="pos")
	except MarkableLevelExistsException:
		pos_level=pd.get_markablelevel_by_name("pos")
	
	# No namespace is available if the level is still empty.
	if not pos_level.get_namespace():
		pos_level.set_namespace(pos_namespace)

	# Go over all sentences
	for sent_m in pd.get_markablelevel_by_name("sentence").get_all_markables():
		# Get a 4-tuple of full string, word list, id list, and (optionally) stringpos-to-id mapping (if mapping=True)
		# We only need the word and is lists
		_, plain_words, word_ids, _ = sent_m.render_string(mapping=False)
		# Use NLTK to pos-tag
		tagged_words = list(zip(nltk.pos_tag(plain_words), word_ids))
		for word_tag_tuple,bd_id in tagged_words:
			# allow_duplicate_spans == False because there can only be one pos tag per word
			is_new, new_m = pos_level.add_markable(spanlists=[[bd_id]], allow_duplicate_spans=False)
			# is_new is false if the markable could not be created. 
			if is_new:
				# Set tag as 'tag' attribute value. Since no annotation scheme validation is active
				# The easiest way to handle this in the annotation scheme is to create a full_text attribute of name 'tag'
				new_m.set_attributes({'tag':word_tag_tuple[1]})
	# Write pos level
	pos_level.write(to_path=pd.get_mmax2_path(full=False)+pd.get_commonpaths().get_markable_path(), overwrite=True)

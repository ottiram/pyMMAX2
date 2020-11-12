import sys, os, codecs, ntpath, pkg_resources, colorama, binascii

from bs4 import BeautifulSoup as bs
from bs4.dammit import EncodingDetector

from xml.sax.saxutils import escape
from colorama import Fore, Back, Style
from unicodedata import category
from collections import OrderedDict
import regex as re

colorama.init()

# Copied from MMAX2 AttributeAPI
NOMINAL_BUTTON 		= 1
NOMINAL_LIST 		= 2
FREETEXT 			= 3
MARKABLE_SET 		= 5
MARKABLE_POINTER 	= 6

ATTRIBUTES 			= {1:'NOMINAL_BUTTON', 2:'NOMINAL_LIST', 3:'FREETEXT', 5:'MARKABLE_SET', 6:'MARKABLE_POINTER'}

MARKABLES_DTD 		= "<!ELEMENT markables (markable*)>\n<!ATTLIST markable id ID #REQUIRED>\n"
WORDS_DTD 			= "<!ELEMENT words (word*)>\n<!ELEMENT word (#PCDATA)>\n<!ATTLIST word id ID #REQUIRED>\n"

SCHEME_STUB 		= "<?xml version='1.0'?>\n<annotationscheme>\n</annotationscheme>\n"
CUSTOMIZATION_STUB 	= "<?xml version='1.0'?>\n<customization>\n</customization>\n"


STYLE_STUB 			= '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0" xmlns:mmax="org.eml.MMAX2.discourse.MMAX2DiscourseLoader">\n\
 					   <xsl:output method="text" indent="no" omit-xml-declaration="yes"/>\n\
                       <xsl:strip-space elements="*"/>\n\
                       <xsl:template match="word">\n\
                       <xsl:value-of select="mmax:registerDiscourseElement(@id)"/>\n\
                       <xsl:apply-templates select="mmax:getStartedMarkables(@id)" mode="opening"/>\n\
                       <xsl:value-of select="mmax:setDiscourseElementStart()"/>\n\
                       <xsl:apply-templates/>\n\
                       <xsl:value-of select="mmax:setDiscourseElementEnd()"/>\n\
                       <xsl:apply-templates select="mmax:getEndedMarkables(@id)" mode="closing"/>\n\
                       </xsl:template>\n\
                       </xsl:stylesheet>'

#####################################################
class MMAX2Discourse(object):                       #
# Main entry point to access .mmax file from Python	#
#####################################################
	# If mmax2_java_binding is available, this will create a 
	# native J_MMAX2DISCOURSE instance to enable access 
	# to the native attribute panels.	
	def __init__(self, mmax2file, common_paths="", verbose=False, max_size=-1, mmax2_java_binding=None):
		if verbose: 
			print(f'\n{Back.GREEN}{Fore.BLACK}{Style.NORMAL}This is {Fore.RED}{Style.BRIGHT}pyMMAX2{Fore.BLACK}{Style.NORMAL}'+
				' version '+pkg_resources.require("PyMMAX2")[0].version+f'{Style.RESET_ALL}', 
				file=sys.stderr)
		self.MMAX2_PROJECT			=	None
		self.COMMONPATHS   			= 	None
		# These are the main references to these two objects
		self.MMAX2_JAVA_BINDING 	=	mmax2_java_binding # This is the jpype reference
		self.J_MMAX2DISCOURSE		=	None

		if self.MMAX2_JAVA_BINDING != None:
			if verbose: print(f'{Fore.MAGENTA}{Style.BRIGHT}MMAX2_JAVA_BINDING available '+ \
				str(self.MMAX2_JAVA_BINDING.JClass('org.eml.MMAX2.core.MMAX2'))+ \
				" " +str(self.MMAX2_JAVA_BINDING.getDefaultJVMPath())+f'{Style.RESET_ALL}', file=sys.stderr)

			# Create and init native Java Discourse object here
			if verbose: print("Calling native Java code to create MMAX2Discourse object\n>>>", file=sys.stderr)
			self.J_MMAX2DISCOURSE = self.MMAX2_JAVA_BINDING.JClass('org.eml.MMAX2.discourse.MMAX2DiscourseLoader')(mmax2file,False,common_paths).getCurrentDiscourse()
			# Set dummy MMAX2 instance (required for some low-level methods)
			self.J_MMAX2DISCOURSE.setMMAX2(self.MMAX2_JAVA_BINDING.JClass('org.eml.MMAX2.core.MMAX2')())
			if verbose: print("<<<\nNative Java code finished", file=sys.stderr)
			if verbose: print(f'{Fore.MAGENTA}{Style.BRIGHT}'+str(self.J_MMAX2DISCOURSE)+f'{Style.RESET_ALL}', file=sys.stderr)

		# Open and read .mmax file
		proj = MMAX2Project(mmax2file, verbose=verbose)
		proj.read(verbose=verbose)	
		# Assign MMAX2_PROJECT to current discourse
		self.MMAX2_PROJECT = proj

		# Expect common_paths.xml in .mmax folder, unless otherwise specified
		full_common_paths=\
			proj.get_mmax2_path()+"common_paths.xml" if common_paths == "" else common_paths

		# Open common_paths.xml
		cp = MMAX2CommonPaths(full_common_paths, discourse=self, verbose=verbose)
		# Read, this includes initializing of all markable levels (no loading of markables, though)
		cp.read(verbose=verbose)

		# Load basedata (this can only happen after cp has been read)
		bd_size=proj.load_basedata(cp, verbose=verbose)
		# Skip loading if max_size is set and bd_size is too high
		if max_size!= -1 and bd_size>max_size:
			raise MaxSizeException("("+str(bd_size)+") "+mmax2file)
		else:
			if verbose: print("\tLoaded "+str(bd_size)+" basedata elements", file=sys.stderr)
		self.COMMONPATHS   = cp 

	# De-coupling the loading of markables (which always includes validation) 
	# from MMAX2Discourse creation is required to allow the creation of a MMAX2Discourse
	# object with invalid attributes. Otherwise, a validation exception would have to be
	# raised from the MMAX2Discourse 'constructor'.
	def load_markables(self, verbose=False):
		# This will collect individual InvalidMMX2AttributeException instances, if any, 
		# and be raised if at least one of these occurred.
		multi_val_exceptions=MultipleInvalidMMAX2AttributeExceptions()
		# This will also load all markables, and init the java-based annotation 
		# scheme class, if mmax2_java_binding is available on DISCOURSE
		self.COMMONPATHS.initialize(self.MMAX2_PROJECT, multi_val_exceptions, verbose=verbose)
		if multi_val_exceptions.get_exception_count()>0:
			raise multi_val_exceptions


	def get_J_MMAX2DISCOURSE(self):
		return self.J_MMAX2DISCOURSE

	def get_mmax2_java_binding(self):
		return self.MMAX2_JAVA_BINDING

	def info(self):
		print("\nMMAX2 Project Info:")
		print("-------------------")
		print(".mmax file        :", f'{Fore.BLUE}'+str(self.MMAX2_PROJECT.get_mmax2_path(full=True))+f'{Style.RESET_ALL}')
		print("Basedata elements :", f'{Fore.BLUE}'+str(self.get_bd_count())+f'{Style.RESET_ALL}')
		print("Markable levels   :")
		for i in self.COMMONPATHS.MARKABLELEVELS:
			def_att_string="Annotation scheme instance not available!"
			default_attrib_list, _ = i.get_default_attributes()
			if default_attrib_list != None:
				def_att_string=""
				for t,a,v,b in default_attrib_list:
					# Mark branching attributes 
					if b:
						a="<>"+str(a)
					def_att_string=def_att_string+str(a)+":"+str(v)+", "
				if def_att_string!="":
					def_att_string=def_att_string[0:-2]
				else:
					def_att_string="none defined"
			print(" "+i.get_name().ljust(16)+" : "+f'{Fore.BLUE}'+str(len(i.get_all_markables()))+f'{Style.RESET_ALL}'+" markables [default: "+f'{Fore.BLUE}'+def_att_string+f'{Style.RESET_ALL}]')

	def get_markablelevel_by_name(self, name, verbose=False):
		r=None
		for i in self.COMMONPATHS.MARKABLELEVELS:
			if i.get_name()==name:
				r=i
				if verbose: print("Found level %s with %s markables (%s)."%(name, str(len(i.get_all_markables())),str(i) ), file=sys.stderr)
				break
		if r == None:
			print("Level %s not found."%name, file=sys.stderr)
		return r


	# This matches cross-basedata, so it is independent of tokenization
	def match_basedata(self, regexes, spanlists, verbose=False, ignore_case=False):
		# regexes is a list of (regex, label) tuples, or just regexes, with a group named <m>
		all_results=[]
		string, pos2id, pos2word=self.render_string(spanlists)
		if ignore_case:
			string=string.lower()

		# Look at each reg individually
		for exp in regexes:
			if not isinstance(exp, tuple):
				exp=(exp,'')

			reg=exp[0]
			label=reg
			if len(exp)>1:
				label=exp[1]

			pos=0
			# Collect lists of span_for_match lists
			results_for_reg=[]

			for match in re.finditer(reg,string,pos):
				group="m"
				start,end=match.span(group)
				span_for_match=[]

				if verbose: print("'%s'"%(match), file=sys.stderr)			
				for t in range(start,end):
					try:
						bd_id=pos2id[t]
					except KeyError:
						# Skip space
						continue
					if len(span_for_match) == 0 or span_for_match[-1]!=bd_id:
						span_for_match.append(bd_id)
				if len(span_for_match)>0:
					results_for_reg.append(([span_for_match],match))
				pos=end-1

			if len(results_for_reg)>0:
				all_results.append((results_for_reg,reg,label))
		return all_results


	def add_markablelevel(self, name, namespace="", scheme="", customization="", create_if_missing=False, encoding='utf-8', dtd_path='"markables.dtd"'):
		ml = MMAX2MarkableLevel(name,
							self,
							namespace=namespace, 
							scheme=scheme, 
							customization=customization, 
							create_if_missing=create_if_missing, 
							dtd_path=dtd_path,
							encoding=encoding)
		self.COMMONPATHS.append_markablelevel(ml)
		return ml


	def render_string(self, brackets=False, mapping=False):
		return (self.get_basedata().render_string(for_ids=None, brackets=brackets, mapping=mapping))


	def get_basedata(self, bd_type="words"):
		return self.MMAX2_PROJECT.get_basedata(bd_type)

	# sort = alpha_asc, alpha_desc, freq_asc, freq_desc
	def get_tf_dict(self, bd_type="words", ignore_case=True, sort="", strip=False, overlay_level=None, verbose=False):
		raw_tf_dict={}
		mwe_tf_dict={}
		processed_markables=set()
		for t in self.MMAX2_PROJECT.get_basedata(bd_type).get_elements():			
			word=t[0]
			if ignore_case:		word=word.lower()
			if strip:			word=word.strip()

			try:				raw_tf_dict[word] += 1    
			except KeyError:	raw_tf_dict[word] = 1

			if overlay_level != None:
#				olms=overlay_level.get_started_markables(t[1])
				olms=overlay_level.get_markables_for_basedata(t[1])
				if len(olms)==0:
					# No overlayed markable
					try:				mwe_tf_dict[word] += 1    
					except KeyError:	mwe_tf_dict[word] = 1
					if verbose: print(word)
				elif len(olms)==1:
					# Count only once
					if olms[0].get_id() not in processed_markables:
						word=olms[0].get_text(self.MMAX2_PROJECT.get_basedata(bd_type))
						if ignore_case:		word=word.lower()
						if strip:			word=word.strip()
						if verbose: print(word)
						try:				mwe_tf_dict[word] += 1
						except KeyError:	mwe_tf_dict[word] = 1
						processed_markables.add(olms[0].get_id())
				else:
					print("Multiple markables not yet supported!")
					pass
			else:
				if verbose: print(word)
				try:				mwe_tf_dict[word] += 1    
				except KeyError:	mwe_tf_dict[word] = 1

		if sort != "":
			if sort ==    "alpha_asc":
				raw_tf_dict = OrderedDict(sorted(raw_tf_dict.items(), key=lambda t: t[0]))
				mwe_tf_dict = OrderedDict(sorted(mwe_tf_dict.items(), key=lambda t: t[0]))				
			elif sort == "alpha_desc":
				raw_tf_dict = OrderedDict(sorted(raw_tf_dict.items(), key=lambda t: t[0], reverse=True))
				mwe_tf_dict = OrderedDict(sorted(mwe_tf_dict.items(), key=lambda t: t[0], reverse=True))				
			elif sort == "freq_asc":
				raw_tf_dict = OrderedDict(sorted(raw_tf_dict.items(), key=lambda t: t[1]))
				mwe_tf_dict = OrderedDict(sorted(mwe_tf_dict.items(), key=lambda t: t[1]))				
			elif sort == "freq_desc":
				raw_tf_dict = OrderedDict(sorted(raw_tf_dict.items(), key=lambda t: t[1], reverse=True))
				mwe_tf_dict = OrderedDict(sorted(mwe_tf_dict.items(), key=lambda t: t[1], reverse=True))				
		return raw_tf_dict, mwe_tf_dict

	def add_basedata_elements_from_string(self, string, bd_type="words"):		
		return self.get_basedata(bd_type=bd_type).add_elements_from_string(string)

	def get_commonpaths(self):
		return self.COMMONPATHS

	def get_mmax2_path(self, full=False):
		return self.MMAX2_PROJECT.get_mmax2_path(full=full)

	def match(self, bd_type="", regexes=[], on_levels=[], attrs_to_match={}, ignore_case=False, verbose=False, teststring=None):
		r=[]
		for l_name in on_levels:
			level=self.get_markablelevel_by_name(l_name)
			for markable in level.get_all_markables():
				if markable.matches_all(attrs_to_match):
					tr=match_basedata(regexes, markable.get_spanlists(), self.get_basedata(bd_type=bd_type), ignore_case=ignore_case, verbose=verbose, teststring=teststring)
					if tr!=[]:
						r.append(tr)
		return r

	def write_all(self):
		self.COMMONPATHS.write()
		self.MMAX2_PROJECT.write()

	def get_bd_count(self, bd_type="words"):
		return len(self.get_basedata(bd_type=bd_type).get_elements())


#################################
class MMAX2MarkableLevel(object):
#################################
	def __init__ (self, name, discourse, 
					file="", namespace="", scheme="", customization="", 
					create_if_missing=False, encoding='utf-8', dtd_path='"markables.dtd"', 
					verbose=False): 
		if verbose: print("Creating markable level", name, file=sys.stderr)
		self.NAME 					= name
		self.FILE 					= file 			if file 			!="" else name+"_markables.xml"
		self.SCHEME 				= scheme 		if scheme 			!="" else name+"_scheme.xml"
		self.CUSTOMIZATION 			= customization if customization 	!="" else name+"_customization.xml"
		self.MARKABLES 				= list()
		self.BASEDATA2MARKABLELISTS = {}
		self.NAMESPACE 				= namespace
		self.ENCODING 				= encoding
		self.DTD_PATH 				= dtd_path
		self.DISCOURSE 				= discourse
		self.J_MMAX2ATTRIBUTEPANEL	= None

		if self.DISCOURSE.get_J_MMAX2DISCOURSE()!=None:
			if verbose: print("Getting reference to native Java MMAX2MarkableLevel "+self.NAME+" ", file=sys.stderr)
			tmp_lev=self.DISCOURSE.get_J_MMAX2DISCOURSE().getMarkableLevelByName(self.NAME,False)
			if verbose: print(f'{Fore.MAGENTA}{Style.BRIGHT}'+str(tmp_lev)+f'{Style.RESET_ALL}', file=sys.stderr)
			self.J_MMAX2ATTRIBUTEPANEL = tmp_lev.getCurrentAnnotationScheme().getCurrentAttributePanel()
			self.J_MMAX2ATTRIBUTEPANEL.setAttributePanelContainer(self.DISCOURSE.get_mmax2_java_binding().JClass('org.eml.MMAX2.gui.windows.MMAX2AttributePanelContainer')())

	def get_J_MMAX2ATTRIBUTEPANEL(self):
		return self.J_MMAX2ATTRIBUTEPANEL

	# This gets a dict of attribute-value pairs and validates it against the current annotation scheme.
	# Validation just makes sure that all attributes and values in the dict are valid, they will *not* be changed.
	# Algorithm: 
	# Go over all default attributes in order.
	# Go over all existing attributes in dict, and try to consume them, by setting their current value to the scheme attribute
	# For branching attributes, this will activate potential dependent attributes, which will be processed recursively
	def validate(self, supplied):
		validation_errors=False
		# av_atts is a dict of plain a-v pairs, representing a markable's attributes on the python/xml level.
		# Copy, because it will be modified		
		invalid 	= supplied.copy()	# Should be empty after validation
		consumed 	= []	# Stores names of attributes that had valid values and could be consumed; will be removed from remaining later
#		invalid 	= {}	# a-v pairs with existing attributes but invalid values
		valid 		= {}
		missing 	= {}	# a-v pairs required by default or as the result of branching attribute setting, but missing in supplied
		if self.J_MMAX2ATTRIBUTEPANEL != None:
			# Reset (invisible) panel to only contain independent attributes with default values.
			self.J_MMAX2ATTRIBUTEPANEL.displayMarkableAttributes(None)
			# Get all default attributes initially. List might be extended in the following.
			# Order is defined by the annotation scheme xml
			current_j_attributes = self.J_MMAX2ATTRIBUTEPANEL.getAllCurrentAttributes()
			ai=0
			# Until all attributes have been processed, including dependent ones
			while ai < len(current_j_attributes):
				# Get current attribute from scheme
				a=current_j_attributes[ai]
				lcn = a.getLowerCasedAttributeName()
#				print(lcn)
				# If this scheme-attribute was found on supplied or not
				lcn_found = False
				# Go over all plain attributes to be validated
				for catt_key in invalid.keys():
					if str(catt_key).lower() == lcn:
						lcn_found=True
#						print("Found",lcn)
						# The current default attribute was found in the supplied ones.
						# Try to set supplied value to attribute in scheme.
						# This will fail if the supplied value is not defined
						a.setSelectedValue(invalid[catt_key],True)
						# If the two values are not identical, setting the value did not work (=invalid)
						if a.getSelectedValue()!=invalid[catt_key]:
							# The current supplied attribute does exist, but it has an invalid value, and will not be consumed
							invalid[catt_key]=invalid[catt_key]
							validation_errors=True
						else:
							# catt_key has been consumed successfully
							consumed.append(catt_key)
							valid[catt_key]=invalid[catt_key]
						if a.getIsBranching():
							# Other, dependent attributes might exist for this attribute it if has the current value
							for dep in a.getNextAttributes(False):
								current_j_attributes.append(dep)
				if not lcn_found:
					missing[lcn]=a.getSelectedValue()
				ai+=1
			for i in consumed:
				del invalid[i]

			# Make sure that *extra* attributes which could not be consumed also trigger a validation exception,
			# just like missing ones
			if len(invalid)>0 or len(missing)>0:
				validation_errors=True
		# validation_errors, valid, extra, supplied = self.LEVEL.validate(attrib_dict)
		return validation_errors, supplied, valid, invalid, missing

	# This returns (None, None) if no connection to annotation scheme is available,
	# and (empty list, empty dict) if no attributes are defined
	def get_default_attributes(self):
		def_att_list=None
		def_att_dict=None
		if self.J_MMAX2ATTRIBUTEPANEL!=None:
			def_att_list=[]
			def_att_dict={}
			# Reset (invisible) panel to only contain independent attributes with default values
			self.J_MMAX2ATTRIBUTEPANEL.displayMarkableAttributes(None)
			for a in self.J_MMAX2ATTRIBUTEPANEL.getAllCurrentAttributes():
				# type, name, val, branching
				def_att_list.append((a.getType(), a.getDisplayAttributeName(), a.getDefaultValue(), a.getIsBranching()))
				# lowercased name, default val
				def_att_dict[a.getLowerCasedAttributeName()]=a.getDefaultValue()
		return def_att_list, def_att_dict


	# Central method for creating markables and adding them to this level
	# Returns (True, new markable) if newly added, (False, existing markable) otherwise. 
	# This adds a mmax_level attribute automatically to every Markable object
	# This is the only method that calls the MMAX2Markable constructor.
	# No validation is done here, since no attributes are processed.
	def add_markable(self, spanlists, m_id="", allow_overlap=True, allow_duplicate_spans=False, apply_default=False, verbose=False):
		existing, overlapping 	= None, None
		empty_span 				= True	# Assume empty span at first
		# Go over span of new markable
		# Outer span
		for span in spanlists:
			# BD per span
			for bd in span:
				empty_span=False
				# Go over all existing markables (if any)
				for m in self.BASEDATA2MARKABLELISTS.get(bd,[]):
					# Check for identity, which is illegal (on the same level!!) if allow_duplicate_spans == False
					#if not allow_duplicate_spans and m.get_span() == spanlists_to_span(spanlists) :# and m.get_attributes() == attribs:
					if not allow_duplicate_spans and m.get_spanlists() == spanlists :# and m.get_attributes() == attribs:
						existing=m
						break
					#if not allow_overlap and      overlap(m.get_span(),      spanlists_to_span(spanlists),self.get_discourse().get_basedata() ):
					#if not allow_overlap and span_overlap(m.get_spanlists(), spanlists, self.get_discourse().get_basedata() ):
					if not allow_overlap and span_overlap(m.get_spanlists(), spanlists):
						overlapping=m
						break
				if existing or overlapping:
					break
			if existing or overlapping:
				break
		if existing:
			if verbose: print("Identical markable exists, skipping",existing.to_xml(), existing.get_spanlists(), file=sys.stderr)
			return (False, existing)
		if overlapping:
			if verbose: print("Overlapping markable exists, and allow_overlap is *False*, skipping",overlapping.to_xml(), overlapping.get_spanlists(), file=sys.stderr)
			return (False, overlapping)

		# Create a new Markable
		if not empty_span:
			# Create id
			m_id = "markable_"+str(len(self.MARKABLES)) if m_id == "" else m_id
			# Create Markable, w/o attributes
			self.MARKABLES.append(MMAX2Markable(spanlists, self, m_id, verbose=verbose))
			# Register
			new_m=self.MARKABLES[-1]
			for spanlist in spanlists:
				for bd in spanlist:
					try:
						self.BASEDATA2MARKABLELISTS[bd].append(new_m)
					except KeyError:
						self.BASEDATA2MARKABLELISTS[bd]=[new_m]
			if apply_default:
				_,def_atts=self.get_default_attributes()
				#print(def_atts)
				new_m.set_attributes(def_atts)
			return (True, self.MARKABLES[-1])
		else:
			print("Not creating markable with empty span on level %s!"%self.NAME, file=sys.stderr)
			return (False, None)


	def get_discourse(self):
		return self.DISCOURSE

	def get_file_name(self):
		return self.FILE

	def set_file_name(self, new_name):
		self.FILE = new_name

	def get_mmax2_java_binding(self):
		return self.MMAX2_JAVA_BINDING

	# Basedata is required here to correctly expand markable spans (by interpolation)
	def load_markables(self, markable_path, basedata, multi_val_exceptions, allow_duplicate_spans=False, verbose=False):
		if verbose: print("Loading markables from", markable_path+self.FILE, file=sys.stderr)
		try:
			with open(markable_path+self.FILE,'r') as ma_in:
				soup=bs(ma_in.read(), 'lxml')
				self.NAMESPACE='xmlns="'+soup.find("markables")['xmlns']+'"'
				dtype=[item for item in soup.contents]# if isinstance(item, bs.Doctype)]
				self.DTD_PATH=dtype[1].split(" ")[2]
				# Go over all markables in xml file
				for m in soup.find_all("markable"):
					# Get all attributes from xml, and make copy because dict will be modified in what follows.
					attrs=m.attrs.copy()
					# This is a meta attribute not stored in the attributes dict
					#del attrs['mmax_level']
					attrs.pop('mmax_level')
					# Dito.
					# Expand short span from xml file *once*, and assign at markable creation
					spanlists=span_to_spanlists(attrs.pop('span'),basedata)
					# Make sure to add the markable from file with the same id, such that pointers are not broken
					id_from_file=attrs.pop('id')
					# newly_added is True if new_m has been newly added
					# Add markable, w/o any attributes yet!
					# This will fail if the span is empty, or if allow_duplicate_spans=False and a markable with the same span exists already.
					(newly_added, new_m) = self.add_markable(spanlists, m_id=id_from_file, verbose=verbose, allow_duplicate_spans=allow_duplicate_spans, allow_overlap=True)
					if newly_added:
						try:
							# This is the only point where this exception is raised
							new_m.set_attributes(attrs, verbose=verbose)
						except InvalidMMAX2AttributeException as exc:
							# exc contains all the details for each individual exception
							multi_val_exceptions.add(exc)
			if verbose: print("\tLoaded",len(self.MARKABLES),"markables to level",self.NAME, file=sys.stderr)		
		except FileNotFoundError:
			print("Markables at "+markable_path +" not found, skipping!", file=sys.stderr)


	def get_name(self):
		return self.NAME

	def get_scheme(self):
		return self.SCHEME

	def get_customization(self):
		return self.CUSTOMIZATION

	def get_file_name(self):
		return self.FILE

	def get_markables_for_basedata(self, bdid):
		try:
			return self.BASEDATA2MARKABLELISTS[bdid]
		except KeyError:
			return []

	def get_started_markables(self, bdid):
		r=[]
		for m in self.get_markables_for_basedata(bdid):
			if m.get_spanlists()[0][0]==bdid:
				r.append(m)
		return r


	def really_erase_markablelevel(self):
		print("Erasing level %s (%s)"%(self.NAME,str(self)))
		self.remove_all_markables()

	def remove_all_markables(self):
		print("Removing %s markables"%str(len(self.MARKABLES)))
		self.MARKABLES=list()
		self.BASEDATA2MARKABLELISTS={}

	def delete_markable(self, deletee):
		# Go over all BD elements that deletee spans
		for bd in flatten_spanlists(deletee.get_spanlists()):
			try:
				self.BASEDATA2MARKABLELISTS[bd].remove(deletee)
			except ValueError:
				pass
		self.MARKABLES.remove(deletee)


	def write(self, to_path="", overwrite=False):
		if to_path=="":
			as_file=self.FILE
		else:
			as_file=to_path+os.path.basename(self.FILE)

		if os.path.exists(as_file) and not overwrite:
			print("File exists and overwrite is FALSE!\n\t",as_file)
			return

		with codecs.open(as_file, mode="w", encoding=self.ENCODING) as bout:
			bout.write('<?xml version="1.0" encoding="'+self.ENCODING.upper()+'"?>\n')
			bout.write('<!DOCTYPE markables SYSTEM '+self.DTD_PATH+'>\n')
			bout.write("<markables "+self.NAMESPACE+">\n")

			for m in self.MARKABLES:
				bout.write(m.to_xml())
			bout.write('</markables>\n')

	def get_markables_by_attributes(self, attrs, join="all"):
		res = []
		if join =="all":
			for m in self.MARKABLES:
				if m.matches_all(attrs):
					res.append(m)
		return res

	def get_all_markables(self):
		return self.MARKABLES

	def is_empty(self):
		return len(self.MARKABLES)==0

###################################################################
class MMAX2Project(object):                                       #
# Light-weight class for handling the diverse MMAX2 project files #
# Does not contain markables, these are handled in commonpaths    #
# Contains loader for initializing the Basedata class             #
###################################################################
	def __init__(self, file, args={}, verbose=False):
		self.FILE  				= file if file.endswith(".mmax") else file+".mmax"
		self.BASEDATA 			= {'words':"", 'gestures':"", 'keyactions':""}
		self.WORDS_FILE 		= ""
		self.GESTURES_FILE 		= ""
		self.KEYACTIONS_FILE	= ""

		if verbose: print("Creating MMAX2Project from "+self.FILE)
		for (k,v) in args.items():
			if k.lower() == "words":
				self.WORDS_FILE=v
				self.BASEDATA['words']=v
			elif k.lower() == "gestures":
				self.GESTURES_FILE=v
				self.BASEDATA['gestures']=v				
			elif k.lower() == "keyactions":
				self.KEYACTIONS_FILE=v
				self.BASEDATA['keyactions']=v
		# Why not read right away??

	def get_basedata(self, bdtype):
		return self.BASEDATA[bdtype]

	def write(self):
		with open(self.FILE, mode="w") as bout:
			bout.write('<?xml version="1.0"?>\n')
			bout.write("<mmax_project>\n")
			bout.write("<words>"+self.WORDS_FILE+"</words>\n")
			bout.write("<gestures>"+self.GESTURES_FILE+"</gestures>\n")			
			bout.write("<keyactions>"+self.KEYACTIONS_FILE+"</keyactions>\n")
			bout.write('</mmax_project>\n')

	def read(self, verbose=False):
		with open(self.FILE, mode="r") as rin:
			if verbose: print("Reading .mmax file at "+str(self.FILE), file=sys.stderr)
			soup = bs(rin.read(), 'lxml')
			try:
				self.WORDS_FILE=soup.find_all("words")[0].text.strip()
				self.BASEDATA["words"]=self.WORDS_FILE
			except IndexError:
				self.WORDS_FILE=""
			try:
				self.GESTURES_FILE=soup.find_all("gestures")[0].text.strip()
				self.BASEDATA["gestures"]=self.GESTURES_FILE								
			except IndexError:
				self.GESTURES_FILE=""
			try:
				self.KEYACTIONS_FILE=soup.find_all("keyactions")[0].text.strip()
				self.BASEDATA["keyactions"]=self.KEYACTIONS_FILE								
			except IndexError:
				self.KEYACTIONS_FILE=""

	def load_basedata(self, commonpaths, verbose=False):
		for (k,v) in [(k,v) for (k,v) in self.BASEDATA.items() if v != ""]:
			if verbose: print("Loading basedata from "+self.get_mmax2_path()+commonpaths.get_basedata_path()+v, file=sys.stderr)
			self.BASEDATA[k]=Basedata(self.get_mmax2_path()+"/"+commonpaths.get_basedata_path()+v, verbose=verbose)
		return len(self.BASEDATA[k].get_elements())

	def get_mmax2_path(self, full=False):
		if not full:
			return os.path.dirname(self.FILE)+"/"
		else:
			return self.FILE

class MMAX2Markable(object):
	# Constructor does not have an attributes parameter. Attributes *must* be set using set_attributes(), which will *always* involve validation.	
	def __init__(self, spanlists, level, m_id="", verbose=False):
		self.LEVEL 		= level 		# This might contain a connection to the underlying MMAX2AnnotationScheme instance 
		# SPANLISTS is a list of lists, where each inner list represents one contiguous sequence of basedata elements.
		self.SPANLISTS 	= spanlists
		self.ID 		= m_id
		self.ATTRIBUTES = {}

	def get_attributes(self):
		return self.ATTRIBUTES

	def to_default(self):
		_,def_atts = self.LEVEL.get_default_attributes()
		self.set_attributes(def_atts)

	# This will *always* set this markable's attributes, but might raise an InvalidMMAX2AttributesException afterwards. 
	def set_attributes(self, attrib_dict, verbose=False):
		validation_errors, supplied, valid, invalid, missing = self.LEVEL.validate(attrib_dict)
		# This makes sure that validation does not modify the supplied attributes
		assert supplied == attrib_dict
		# Set, regardless of possible validation errors
		self.ATTRIBUTES = attrib_dict
		if verbose:
			print(self.ATTRIBUTES)
		if validation_errors:
			raise InvalidMMAX2AttributeException(self.LEVEL.get_name(), self.ID, supplied, valid, invalid, missing)

	def remove_attribute(self, attname, validate=False):
		del self.ATTRIBUTES[attname]
		if validate:
			# Trigger validation by explicity re-setting attributes
			self.set_attributes(self.ATTRIBUTES)

	# Delete this markable from its level, also remove it from BASEDATA-Mappings
	def delete(self):
		self.LEVEL.delete_markable(self)

	def to_xml(self):
		st='<markable id="'+self.ID+'" span="'+spanlists_to_span(self.SPANLISTS)+'" mmax_level="'+self.LEVEL.get_name()+'"'
		for (k,v) in self.ATTRIBUTES.items():
			st=st+' '+str(k)+'="'+str(v)+'"'
		st=st+'/>\n'
		return st

	def render_string(self, brackets=False, mapping=False):
		return (self.LEVEL.get_discourse().get_basedata().render_string(for_ids=self.SPANLISTS, brackets=brackets, mapping=mapping))

	# This should not be necessary, use spanlists_to_span directly
#	def get_span(self):
#		return spanlists_to_span(self.SPANLISTS)

	def get_spanlists(self):
		return self.SPANLISTS

	def matches_all(self,attrs):
		m=True
		if len(attrs)>0:	# Empty attrs matches always
			for k,v in attrs.items():
				if v.startswith("***"):
					v=v[3:]
					# v is a regexp
					try:
						# re.match returns None and not False
						if re.match(v,self.ATTRIBUTES[k])==None:
							m=False
							break
					except KeyError:
						m=False
						break
				else:
					try:
						if self.ATTRIBUTES[k]!=v:
							m=False
							break
					except KeyError:
						m=False
						break
		return m

	def get_id(self):
		return self.ID

#	def get_text(self):
#		return self.LEVEL.get_discourse().render_string(self.get_spanlists())[0]

###############################################################
class MMAX2CommonPaths(object):                               #
# Middle-weight class for handling system files and markables #
# Contains reference to py-discourse object, and loader for   #
# markable level class
###############################################################
	def __init__(self, file, discourse=None, markablelevels=None, views=None, args=None, verbose=False):
		self.FILE 				= file
		self.SCHEME_PATH 		= ""
		self.STYLE_PATH 		= ""
		self.BASEDATA_PATH 		= ""
		self.CUSTOMIZATION_PATH = ""
		self.MARKABLE_PATH 		= ""
		self.VIEWS 				= views 		 if views          != None else ['generic_nongui_style.xsl']
		self.MARKABLELEVELS 	= markablelevels if markablelevels != None else []
		self.DISCOURSE 			= discourse

		if args != None:
			for (k,v) in args.items():
				if k.lower() 	== "scheme_path":
					self.SCHEME_PATH=v
				elif k.lower() 	== "style_path":
					self.STYLE_PATH=v
				elif k.lower() 	== "basedata_path":
					self.BASEDATA_PATH=v
				elif k.lower() 	== "customization_path":
					self.CUSTOMIZATION_PATH=v
				elif k.lower() 	== "markable_path":
					self.MARKABLE_PATH=v

		# Get location of this common_paths xml file
		def_style_path = os.path.dirname(self.FILE)+self.STYLE_PATH
		if os.path.isdir(def_style_path)==False:
			os.mkdirs(def_style_path)
		if os.path.isfile(def_style_path+"/generic_nongui_style.xsl")==False:
			with open(def_style_path+"/generic_nongui_style.xsl", 'w') as wout:
				wout.write(STYLE_STUB)


	def get_basedata_path(self):
		return self.BASEDATA_PATH

	def get_commonpaths_path(self):
		return os.path.dirname(self.FILE)+"/"

	# This is called by the load_markables() method of the MMAX2Discourse constructor.
	# It expands the markable file variable ($), if it exists, and calls
	# load_markables() on every level.
	# multi_val_exceptions is passed to each of the latter calls, collecting all 
	# markable-level validation errors.
	def initialize(self, mmax2proj, multi_val_exceptions, verbose=False):
		for ml in self.MARKABLELEVELS:
			# Replace project name placeholder $ with actual project names
			# Use .mmax file basename - last 5 chars (.mmax)
			if ml.get_file_name().find("$")!=-1:
				ml.set_file_name(ml.get_file_name().replace("$", ntpath.basename(mmax2proj.FILE)[0:-5]))
			if verbose: 
				print("Probing annotation scheme at "+mmax2proj.get_mmax2_path()+self.SCHEME_PATH+ml.get_scheme(), file=sys.stderr)
				if os.path.exists(mmax2proj.get_mmax2_path()+self.SCHEME_PATH+ml.get_scheme()):
					print(f'\t{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}SUCCESS{Style.RESET_ALL}', file=sys.stderr)
				else:
					print(f'\t{Back.RED}{Fore.BLACK}{Style.BRIGHT}FAILURE{Style.RESET_ALL}', file=sys.stderr)
			ml.load_markables(mmax2proj.get_mmax2_path()+self.MARKABLE_PATH, mmax2proj.get_basedata(bdtype="words"), multi_val_exceptions, verbose=verbose)

	def append_markablelevel(self, ml):
		self.MARKABLELEVELS.append(ml)

	def write(self, overwrite=False):
		if not os.path.exists(self.FILE) or overwrite:
			with open(self.FILE, mode="w") as bout:
				bout.write('<?xml version="1.0"?>\n')
				bout.write("<common_paths>\n")
				bout.write("<scheme_path>"			+self.SCHEME_PATH+"</scheme_path>\n")
				bout.write("<style_path>"			+self.STYLE_PATH+"</style_path>\n")			
				bout.write("<basedata_path>"		+self.BASEDATA_PATH+"</basedata_path>\n")
				bout.write("<customization_path>"	+self.CUSTOMIZATION_PATH+"</customization_path>\n")			
				bout.write("<markable_path>"		+self.MARKABLE_PATH+"</markable_path>\n")			
				bout.write("<views>\n")
				for n in self.VIEWS:
					bout.write("<stylesheet>"+n+"</stylesheet>\n")
				bout.write("</views>\n")			
				bout.write("<annotations>\n")
				for m in self.MARKABLELEVELS:
					bout.write('<level name="'+m.get_name()+'" schemefile="'+m.get_scheme()+'" customization_file="'+m.get_customization()+'">'+m.get_file_name()+'</level>\n')
				bout.write("</annotations>\n")			
				bout.write('</common_paths>\n')

	def read(self, verbose=False):
		with open(self.FILE, mode="r") as rin:
			if verbose: print("Reading common paths info from "+str(self.FILE), file=sys.stderr)
			soup = bs(rin.read(), 'lxml')
			try:
				self.SCHEME_PATH=soup.find_all("scheme_path")[0].text
			except IndexError:
				self.SCHEME_PATH=""
			try:
				self.STYLE_PATH=soup.find_all("style_path")[0].text
			except IndexError:
				self.STYLE_PATH=""
			try:
				self.BASEDATA_PATH=soup.find_all("basedata_path")[0].text
			except IndexError:
				self.BASEDATA_PATH=""
			try:
				self.CUSTOMIZATION_PATH=soup.find_all("customization_path")[0].text
			except IndexError:
				self.CUSTOMIZATION_PATH=""
			try:
				self.MARKABLE_PATH=soup.find_all("markable_path")[0].text
			except IndexError:
				self.MARKABLE_PATH=""
			try:
				for s in soup.find_all("views")[0].find_all("stylesheet"):			
					self.VIEWS.append(s.text)
			except IndexError:
				self.VIEWS=[]			
			try:
				for s in soup.find_all("annotations")[0].find_all("level"):
					level = MMAX2MarkableLevel(s['name'], 
											self.DISCOURSE,
											s.text,
											namespace=s['name'], 
											scheme=s['schemefile'], 
											customization=s['customization_file'], 
											create_if_missing=False, 
											encoding='utf-8',
											verbose=verbose)
					self.MARKABLELEVELS.append(level)
			except IndexError:
				self.MARKABLELEVELS=[]

#######################
class Basedata(object):
#######################	
	def __init__ (self, filename, bdtype='word', encoding='utf-8', verbose=False):
		self.BDTYPE=bdtype
		self.FILENAME=filename
		self.DCELEMENTS=list()
		self.TAGS={}
		self.BDID2LISTPOS={}

		# Set encoding from supplied file
		if os.path.exists(self.FILENAME):
			with open(self.FILENAME,"r") as win:
				raw=win.read()
				self.ENCODING = EncodingDetector.find_declared_encoding(raw, is_html=False)
				soup = bs(raw, 'lxml')				
			for w in soup.find_all(self.BDTYPE):
				# dcelement = tuple of (string, id, discpos, attribs)				
				atts=None
				for att in w.attrs:
					if att!="id":
						# Create bd-level attributes only if needed
						if not atts:
							atts = {}
						atts[att]=w.attrs[att]
				self.DCELEMENTS.append((w.get_text(), w['id'], len(self.DCELEMENTS), atts))
				self.BDID2LISTPOS[w['id']]=len(self.DCELEMENTS)-1			
		else:
			# Set supplied encoding (for Basedata yet to be created)
			self.ENCODING=encoding		

	# Returns bd_id span	
	def add_elements_from_string(self, uc_string):
		bd_ids=[]
		w=""
		spaces=0
		# Go through input string
		# Get current char
		for i in uc_string:
			if category(i) in ['Sc', 'Sm', 'So', 'Zl','Zp', 'Zs', 'Pc', 'Pd','Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Cf', 'Cc']:
				# Current char is a saveable separator OR a space
				# Save current token *before* separator, if any
				if w != "":
					# We have accumulated some token
					# spc is the number of spaces to be rendered *before* this token, 
					# so the current one (if it is one) should not count here!
					# Save token accumulated so far.
					if spaces !=1:
						bd_ids.append(self.add_element(w, bd_attribs={'spc':str(spaces)}))
					else:
						bd_ids.append(self.add_element(w))
					# Reset token accumulated so far
					w=""
					spaces=0

				if category(i) not in ['Zl','Zp', 'Zs', 'Cf', 'Cc']:
					# Save separator, unless a space or newline
					if spaces !=1:
						bd_ids.append(self.add_element(i, bd_attribs={'spc':str(spaces)}))
					else:
						bd_ids.append(self.add_element(i))
					# Reset space counter
					spaces=0
				else:
					spaces+=1
			else:
				# Current char is not a separator, collect char for token
				w+=i
		if w != "":
			# We have accumulated some token
			# spc is the number of spaces to be rendered *before* this token, 
			# so the current one (if it is one) should not count here!
			# Save token accumulated so far.
			if spaces !=1:
				bd_ids.append(self.add_element(w, bd_attribs={'spc':str(spaces)}))
			else:
				bd_ids.append(self.add_element(w))
		return bd_ids


	def render_string(self, for_ids=None, brackets=False, mapping=False):
		m_string=""
		pos2id={}
		last_pos=0
		words=[]
		ids=[]
		if not for_ids:
			for_ids=[[]]
			# dcelement = tuple of (string, id, discpos, attribs)
#			print(self.DCELEMENTS)
			for _, bdid, _, _ in self.DCELEMENTS:
				for_ids[0].append(bdid)

		for spanlist in for_ids:
			for sid, bd_id in enumerate(spanlist):
				te=self.get_element_text(bd_id)
				atts=self.get_element_attributes(bd_id)
				if not atts:
					l_spaces=1
				else:
					# Default 1 is correct because one space is the default
					l_spaces=int(atts.get('spc','1'))
				# Create pad
				pad=" "*l_spaces
				last_pos=len(m_string)+l_spaces
				# Add spaces *before* te
				m_string=m_string+pad+te
				if mapping:
					# Create mapping of char positions covered by te to bd_id
					for i in range(last_pos, last_pos+len(te)):
						pos2id[i]=bd_id
				words.append(te)
				ids.append(bd_id)
			m_string="["+m_string+"]" if brackets else m_string
		return m_string, words, ids, pos2id


	# Returns bd_id
	def add_element(self, bd_text, bd_attribs=None):
		bd_id=self.BDTYPE+"_"+str(len(self.DCELEMENTS))
		# text, id, pos, attributes
		self.DCELEMENTS.append((bd_text, bd_id, len(self.DCELEMENTS), bd_attribs))
		self.BDID2LISTPOS[bd_id]=len(self.DCELEMENTS)-1		
		return bd_id


	# This matches cross-basedata, so it is independent of tokenization
	def match_string(self, regexes, for_ids=None, ignore_case=False, verbose=False):
		# regexes is a list of (regex, label) tuples, where label is optional
		all_results=[]
		string, words, _, pos2id=self.render_string(for_ids=for_ids, mapping=True)
		if ignore_case:
			string=string.lower()

		# Look at each reg individually
		for exp in regexes:
			reg=exp[0]
			# Default: Use reg as label
			label=reg
			# Explicit label has been supplied
			if len(exp)>1:
				label=exp[1]
			pos=0
			# Collect lists of span_for_match lists
			results_for_reg=[]

			for match in re.finditer(reg,string,pos):
				# None or one capturing group only
				group="m"
				start, end=match.span(group)
				span_for_match=[]
				if verbose: print("'%s'"%(match), file=sys.stderr)			
				for t in range(start, end):
					try:
						bd_id=pos2id[t]
					except KeyError:
						# Skip space
						continue
					if len(span_for_match) == 0 or span_for_match[-1]!=bd_id:
						span_for_match.append(bd_id)
				if len(span_for_match)>0:
					#results_for_reg.append(([span_for_match],match))
					results_for_reg.append([span_for_match])
				pos=end-1
			if len(results_for_reg)>0:
				all_results.append((results_for_reg,reg,label))
		return all_results


	def get_elements(self):
		return self.DCELEMENTS

	def get_element(self, bd_id):
		return self.DCELEMENTS[self.BDID2LISTPOS[bd_id]]

	def get_element_text(self, bd_id):
		return self.DCELEMENTS[self.BDID2LISTPOS[bd_id]][0]

	def get_element_attributes(self, bd_id):
		return self.DCELEMENTS[self.BDID2LISTPOS[bd_id]][3]

	def write(self, to_path="", dtd_base_path='"../', overwrite=False):
		if to_path=="":
			as_file=self.FILENAME
		else:
			as_file=to_path+os.path.basename(self.FILENAME)

		if os.path.exists(as_file) and not overwrite:
			print("File exists and overwrite is FALSE!\n\t",as_file)
			return

		with codecs.open(as_file, mode="w", encoding=self.ENCODING) as bout:
			bout.write('<?xml version="1.0" encoding="'+self.ENCODING.upper()+'"?>\n')
			bout.write('<!DOCTYPE '+self.BDTYPE+'s SYSTEM '+dtd_base_path+self.BDTYPE+'s.dtd">\n')
			bout.write("<"+self.BDTYPE+"s>\n")
			for b in self.DCELEMENTS:
				st='<'+self.BDTYPE+' id="'+b[1]+'"'
				if b[3] != None:
					for (k,v) in b[3].items():
						st=st+' '+k+'="'+v+'"'
				bout.write(st)
				bout.write('>'+escape(b[0])+'</word>\n')
				#bout.write('>'+b[0].encode(self.ENCODING)+'</word>\n')
			bout.write('</words>\n')

		
	def delete_all_elements(self):
		self.DCELEMENTS=list()
		self.BDID2LISTPOS={}


	def interpolate_span(self, first_id, last_id):
		r=[]
		collecting=False
		for i in self.DCELEMENTS:
			if i[1]==first_id:
				collecting=True
			if collecting: 
				r.append(i[1])
			if i[1]==last_id:
				break
		return r

	def get_preceeding_elements(self, bd_id, width=10):
		for (pos,i) in enumerate(self.DCELEMENTS):
			if i[1]==bd_id:
				start_pos=pos
				break
		pad=False
		if start_pos-width<0:
			width=start_pos
			pad=True
		return(self.DCELEMENTS[start_pos-width:start_pos], pad)

	def get_following_elements(self, bd_id, width=10):
		for (pos,i) in enumerate(self.DCELEMENTS):
			if i[1]==bd_id:
				start_pos=pos+1
				break
		pad=False
		if start_pos+width>=len(self.DCELEMENTS):
			width=len(self.DCELEMENTS)
			pad=True
		return(self.DCELEMENTS[start_pos:start_pos+width], pad)



# Static helper methods
#############################################



##############################
class PhraseAnnotator(object):
##############################	
	def __init__ (self, phrasefile, ignore_case=True):
		self.PHRASES=set()
		self.IGNORE_CASE=ignore_case
		self.MAX_LEN=0

		with open(phrasefile) as pin:
			for p in pin:
				p=p.strip()
				if p!="":
					if len(p.split(" "))>self.MAX_LEN:	
						self.MAX_LEN=len(p.split(" "))
					if self.IGNORE_CASE:	
						p=p.lower()
					self.PHRASES.add(p)
		print("PhraseAnnotator loaded",len(self.PHRASES),"phrases, ignore_case",self.IGNORE_CASE, "max phrase length",self.MAX_LEN)

	def apply(self, bdata, targetlevel, attribs, verbose=False):
		elems=len(bdata.DCELEMENTS)
		# Move through tokens from left to right. There should be *one* o pass only
		for o in range(elems):
			elems=len(bdata.DCELEMENTS)
			# Move through tokens from right to left, start at o+MAX_LEN (no phrase will be longer)
			for n in range(self.MAX_LEN+o,o,-1):	# o instead of o-1 will also find single-token phrases
				if n > elems: 
					n=elems
					elems-=1
				ngram=""
				for t in range(o,n):
					print(t)
					ngram=ngram+" "+bdata.DCELEMENTS[t][0]
					ngram=ngram.strip()
				if self.IGNORE_CASE:
					ngram=ngram.lower()
				if ngram in self.PHRASES:
					if verbose: 
						print("Found phrase '%s' from %s to %s"%(ngram,str(o), str(n-1)))
					spanlist=[bd[1] for bd in bdata.DCELEMENTS[o:ngram]]
					targetlevel.add_markable([spanlist], attribs)			

def kwic_string_for_elements(bd_id_list, basedata, width=5, fillwidth=100, lsep="_>>", rsep="<<_"):
# continuous elements only
#	m_start=markable.get_spanlists()[0][0]
#	m_end=markable.get_spanlists()[-1][-1]
	pre_bd, lpadded=basedata.get_preceeding_elements(bd_id_list[0], width=width)
	fol_bd, rpadded=basedata.get_following_elements(bd_id_list[-1], width=width)
	lc,rc="",""

	if lpadded:	lc="*B_O_BDATA*"
	for text,spc in [(t[0], int(t[3].get('spc','1'))) for t in pre_bd]:
		lc=lc+(" "*spc)+text
	for text,spc in [(t[0], int(t[3].get('spc','1'))) for t in fol_bd]:
		rc=rc+(" "*spc)+text

	if rpadded:
		rc=" "+rc+ "*E_O_BDATA*"
	else:
		rc=" "+rc
	bd_elem_string=render_string([bd_id_list], basedata, brackets=False, mapping=False)[0]
	lc=lc+lsep
	return lc.rjust(fillwidth)+bd_elem_string+rsep+rc



# This matches cross-basedata, so it is independent of tokenization
def match_basedata_bak(regexes, spanlists, ignore_case=False, verbose=False):
	# regexes is a list of (regex, label, sample) tuples, label is optional
	all_results=[]

#	testing=False
#	if teststring != None:
#		string=teststring
#		testing=True
#		verbose=True

#	if not testing:
	string, pos2id, pos2word=render_string(spanlists)
#	else:
#		pos2id={}
#		pos2word={}
	if ignore_case:
		string=string.lower()

	# Look at each reg individually
	for exp in regexes:
		reg=exp[0]
		label=reg
		if len(exp)>1:
			label=exp[1]

		if testing:
			print("\n"+reg)
			print("\n"+string)

		pos=0
		# Collect lists of span_for_match lists
		results_for_reg=[]

		for match in re.finditer(reg,string,pos):
			# None or one capturing group only
#			group=0 if not match.groups() else 1
#			if verbose: print(match.span(group))
			group="m"

			start,end=match.span(group)
			span_for_match=[]

			if verbose: print("'%s'"%(match), file=sys.stderr)			
			for t in range(start,end):
				try:
					bd_id=pos2id[t]
				except KeyError:
					# Skip space
					continue
				if len(span_for_match) == 0 or span_for_match[-1]!=bd_id:
					span_for_match.append(bd_id)
			if len(span_for_match)>0:
				results_for_reg.append(([span_for_match],match))
			pos=end-1

		if len(results_for_reg)>0:
			all_results.append((results_for_reg,reg,label))
	return all_results


# spanlists is a list with one list per segment
# This should only be necessary when serializing a markable to xml
def spanlists_to_span(spanlists):
	span=""
	for spanlist in spanlists:
		if len(spanlist)==1:
			span=spanlist[0]+","
		else:
			span=span+spanlist[0]+".."+spanlist[-1]
			span=span+","
	return span[:-1]


def span_to_spanlists(span, basedata):
	spanlists=[]
	# Discont markables have more than one segment
	for seg in span.split(","):
		spanlist=[]
		if seg.find("..")>-1:
			spanlist=basedata.interpolate_span(seg.split("..")[0],seg.split("..")[1])
		else:
			spanlist=[seg]
		spanlists.append(spanlist)
	return spanlists


def span_overlap(full_span1, full_span2):
#	full_span1=span_to_spanlists(span1, basedata)
#	full_span2=span_to_spanlists(span2, basedata)

	if set(flatten_spanlists(full_span1)).intersection(set(flatten_spanlists(full_span2))) != {}:
		return True
	return False

def flatten_spanlists(spanlists):
	return [item for sublist in spanlists for item in sublist]

#def pythonify_MMAX2Attribute(mmax2att):
#	print(mmax2att.getDisplayAttributeName())


#def int2bytes(i):
#    hex_string = '%x' % i
#    n = len(hex_string)
#    return binascii.unhexlify(hex_string.zfill(n + (n & 1)))

#def split_utf8(s, n=1):
##	print(type(s))#
#	start = 0
#	lens = len(s)
#	print(lens)
#	while start < lens:
#		if lens - start <= n:
#			yield s[start:]
#			return # StopIteration
#		end = start + n
#		print(2,type(s[end]), type(0x80))
#		while 0x80 <= s[end] <= 0xBF:
#			end -= 1
#		assert end > start
#		yield s[start:end]
#		start = end

#######################################
# Exceptions
# This one is only raised on the level of the individual markable.
class InvalidMMAX2AttributeException(Exception):
	def __init__(self, level, m_id, supplied_attribs, valid_attribs, extra_attribs, missing_attribs):
		self.supplied_attribs 	= supplied_attribs
		self.valid_attribs 		= valid_attribs
		self.extra_attribs 		= extra_attribs
		self.missing_attribs 	= missing_attribs
		self.m_id 				= m_id
		self.level 				= level
		self.message = "\nOne or more of the following attributes are invalid for markable "+self.m_id+" on level "+self.level+"!"
		# Call Exception super class
		super().__init__(self.message)

	def __str__(self):
		return '\n\nLevel: '+ self.level+', ID: ' + self.m_id + f'\n{Fore.BLACK}{Style.NORMAL}Supplied: ' + str(self.supplied_attribs)+f'\n{Fore.BLACK}{Back.GREEN}{Style.NORMAL}Valid:    '+str(self.valid_attribs)+f'{Style.RESET_ALL}\n{Fore.YELLOW}{Back.RED}{Style.NORMAL}Invalid:  '+str(self.extra_attribs)+f'{Style.RESET_ALL}\n{Fore.YELLOW}{Back.RED}{Style.NORMAL}Missing:  '+str(self.missing_attribs)+f'{Style.RESET_ALL}'


class MultipleInvalidMMAX2AttributeExceptions(Exception):
	def __init__(self):
		self.exceptions = []
		self.message = "\nThere were one or more instances of InvalidMMAX2AttributeException!"
		# Call Exception super class
		super().__init__(self.message)

	def add(self, exc):
		self.exceptions.append(exc)

	def get_exception_count(self):
		return len(self.exceptions)		

	def get_exception_at(self,i):
		return self.exceptions[i]

	def __str__(self):
		mess=""
		for i in self.exceptions:
			mess=mess+str(i)
		return self.message+mess

class MaxSizeException(Exception):
	pass
# -*- coding: utf-8 -*-

# Copyright 2008 Jaap Karssenberg <jaap.karssenberg@gmail.com>

'''This module handles parsing and dumping input in plain text'''

import re

from zim.formats import *
from zim.parsing import TextBuffer, url_re

info = {
	'name': 'plain',
	'desc': 'Plain text',
	'mimetype': 'text/plain',
	'extension': 'txt',
	'native': False,
	'import': True,
	'export': True,
}


bullets = {
	'[ ]': UNCHECKED_BOX,
	'[x]': XCHECKED_BOX,
	'[*]': CHECKED_BOX,
	'*': BULLET,
}
# reverse dict
bullet_types = {}
for bullet in bullets:
	bullet_types[bullets[bullet]] = bullet


class Parser(ParserClass):

	# TODO parse constructs like *bold* and /italic/ same as in email,
	# but do not remove the "*" and "/", just display text 1:1

	# TODO also try at least to parse bullet and checkbox lists
	# common base class with wiki format

	# TODO parse markdown style headers

	def parse(self, input):
		if isinstance(input, basestring):
			input = input.splitlines(True)

		input = url_re.sublist(
			lambda match: ('link', {'href':match[1]}, match[1]) , input)


		builder = TreeBuilder()
		builder.start('zim-tree')

		for item in input:
			if isinstance(item, tuple):
				tag, attrib, text = item
				builder.start(tag, attrib)
				builder.data(text)
				builder.end(tag)
			else:
				builder.data(item)

		builder.end('zim-tree')
		return ParseTree(builder.close())


class Dumper(DumperClass):

	# We dump more constructs than we can parse. Reason for this
	# is to ensure dumping a page to plain text will still be
	# readable.

	# TODO check commonality with dumper in wiki.py

	def dump(self, tree):
		#~ print 'DUMP PLAIN', tree.tostring()
		assert isinstance(tree, ParseTree)
		output = TextBuffer()
		self.dump_children(tree.getroot(), output)
		return output.get_lines(end_with_newline=not tree.ispartial)

	def dump_children(self, list, output, list_level=-1, list_type=None, list_iter='0'):
		if list.text:
			output.append(list.text)

		for element in list.getchildren():
			if element.tag in ('p', 'div'):
				indent = 0
				if 'indent' in element.attrib:
					indent = int(element.attrib['indent'])
				myoutput = TextBuffer()
				self.dump_children(element, myoutput) # recurs
				if indent:
					myoutput.prefix_lines('\t'*indent)
				output.extend(myoutput)
			elif element.tag == 'h':
				## Copy from Markdown
				level = int(element.attrib['level'])
				if level < 1:   level = 1
				elif level > 5: level = 5

				if level in (1, 2):
					# setext-style headers for lvl 1 & 2
					if level == 1: char = '='
					else: char = '-'
					heading = element.text
					line = char * len(heading)
					output.append(heading + '\n')
					output.append(line)
				else:
					# atx-style headers for deeper levels
					tag = '#' * level
					output.append(tag + ' ' + element.text)
			elif element.tag in ('ul', 'ol'):
				indent = int(element.attrib.get('indent', 0))
				start = element.attrib.get('start')
				myoutput = TextBuffer()
				self.dump_children(element, myoutput, list_level=list_level+1, list_type=element.tag, list_iter=start) # recurs
				if indent:
					myoutput.prefix_lines('\t'*indent)
				output.extend(myoutput)
			elif element.tag == 'li':
				if 'indent' in element.attrib:
					# HACK for raw trees from pageview
					list_level = int(element.attrib['indent'])

				if list_type == 'ol':
					bullet = str(list_iter) + '.'
					list_iter = increase_list_iter(list_iter) or '1' # fallback if iter not valid
				else:
					bullet = bullet_types[element.attrib.get('bullet', BULLET)]
				output.append('\t'*list_level+bullet+' ')
				self.dump_children(element, output, list_level=list_level) # recurs
				output.append('\n')
			elif element.tag == 'img':
				src = element.attrib['src']
				opts = []
				for k, v in element.attrib.items():
					if k == 'src' or k.startswith('_'):
						continue
					else:
						opts.append('%s=%s' % (k, v))
				if opts:
					src += '?%s' % '&'.join(opts)
				if element.text:
					output.append(element.text)
				else:
					output.append(src)
			elif element.tag == 'link':
				assert 'href' in element.attrib, \
					'BUG: link %s "%s"' % (element.attrib, element.text)
				href = element.attrib['href']
				if element.text:
					output.append(element.text)
				else:
					output.append(href)
			elif element.tag == 'pre':
				indent = 0
				if 'indent' in element.attrib:
					indent = int(element.attrib['indent'])
				myoutput = TextBuffer()
				myoutput.append(element.text)
				if indent:
					myoutput.prefix_lines('\t'*indent)
				output.extend(myoutput)
			elif element.text:
				output.append(element.text)
			else:
				pass

			if element.tail:
				output.append(element.tail)

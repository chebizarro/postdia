#!/usr/bin/env python

#   Postgres SQL import export goodness
#   Copyright (C), 2013 Chris Daley <chebizarro@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This module implements a Postgres SQL import and export dialog to connect
# to a Postgres SQL database server as well as an export module to dump a diagram
# to Postgres SQL compatible SQL.
#

import sys, math, types, string, re

# Make sure we use pygtk for gtk 2.0
import pygtk
pygtk.require("2.0")

import gtk
import gtk.keysyms
import gobject

import psycopg2
import psycopg2.extras

class SQLRenderer :
	def __init__ (self) :
		pass
		
	def begin_render (self, data, filename) :
		self.f = open(filename, "w")
		self.sql = DiaSql(data)
		self.sql.generateSQL()
		self.f.write(self.sql.SQL)

	def end_render (self) :
		self.f.close()


class DiaSql :
	
	reserved = ["all","analyse","analyze","and","any","array","as","asc","asymmetric","both","case","cast","check","collate","column","constraint","create","current_catalog","current_date","current_role","current_time","current_timestamp","current_user","default","deferrable","desc","distinct","do","else","end","except","false","fetch","for","foreign","from","grant","group","having","in","initially","intersect","into","lateral","leading","limit","localtime","localtimestamp","not","null","offset","on","only","or","order","placing","primary","references","returning","select","session_user","some","symmetric","table","then","to","trailing","true","union","unique","user","using","variadic","when","where","window","with","authorization","binary","collation","concurrently","cross","current_schema","freeze","full","ilike","inner","is","isnull","join","left","like","natural","notnull","outer","over","overlaps","right","similar","verbose"]
	
	def __init__(self, data) :
		self.data = data
		self.layer = data.active_layer
		self.SQL = "--\n-- PostgreSQL database dump\n--\n\n\n"
		self.SQL += "CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;\n\n"

	def generateSQL(self) :
		TSQL = ""
		SSQL = ""
		CSQL = ""
		
		for obj in self.layer.objects :
			if str(obj.type) == "UML - Class" :
				TSQL += self.generateTable(obj)
			elif str(obj.type) == "UML - SmallPackage" :
				SSQL += self.generateSequence(obj)
			elif str(obj.type) == "UML - Constraint" :
				CSQL += self.generateConstraint(obj)
				
		self.SQL += SSQL + TSQL + CSQL

	def generateTable(self, obj) :
		noprops = len(obj.properties.get("attributes").value)
		idx = 1
		pattern = r"'(.*?)'"
		seq = ""
		seqCol = ""
		tableName = obj.properties.get("name").value

		if tableName in self.reserved :
			tableName = '"' + tableName + '"'
			
		sql = "CREATE TABLE " + tableName + " (\n"

		for att in obj.properties.get("attributes").value :
			#(name,type,value,comment,visibility,abstract,class_scope)
			quotes = ""
			if att[4] == 2 :
				m = re.search(pattern, att[2])
				if m != None :
					seq = m.group()
					seqCol += "ALTER SEQUENCE " + seq.strip("'") + " OWNED BY " + tableName + "." + att[0] + ";\n\n"

			if att[0] in self.reserved :
				quotes = '"'
			sql += "\t" + quotes + att[0] + quotes + " " + att[1] + " " + att[2]
			if idx < noprops:
				sql += ","
			sql += "\n"
			idx += 1
		sql += ");\n\n"
		
		sql += seqCol
		
		# create indices
		# (name, type, comment, stereotype, visibility, inheritance_type, query,class_scope, params)
		for op in obj.properties.get("operations").value :
			if op[1] == "primary key" :
				sql += "ALTER TABLE ONLY " + tableName + "\n ADD CONSTRAINT " + op[0] + " PRIMARY KEY (" + op[8][0][0] + ");\n\n"
			else :		
				sql += "CREATE "
				if op[1] == "unique index" :
					sql += "UNIQUE "
				sql += "INDEX " + op[0] + " ON " + tableName + " USING btree (" + op[8][0][0] + ");\n\n" 
		
		return sql
		
	def generateSequence(self, obj) :
		return "\n" + str(obj.properties["text"].value.text) + "\n\n"
		
	def generateConstraint(self, obj) :
		t1 = obj.handles[0].connected_to.object
		t2 = obj.handles[1].connected_to.object
		idxname = self.getConnectedField(obj, t1, 0)
		tgtname = self.getConnectedField(obj, t2, 1)
		sql = "ALTER TABLE ONLY " + t1.properties.get("name").value + "\n"
		sql += "\tADD CONSTRAINT " + obj.properties.get("constraint").value + " FOREIGN KEY ("
		sql += idxname + ") REFERENCES " + t2.properties.get("name").value +"(" + tgtname + ") ON UPDATE SET NULL ON DELETE SET NULL DEFERRABLE;\n\n"
		return sql
	
	def getConnectedField(self, obj1, obj2, handle) :
		cnt = 0
		for i in obj2.connections :
			if i == obj1.handles[handle].connected_to :
				break
			cnt+=1
		idx = 0
		idxname = ""	
		for att in obj2.properties.get("attributes").value :
			if idx == ((cnt-8)/2) :
				idxname = att[0]
				break
			idx += 1		
		return idxname
	
	def printSQL(self) :
		print self.SQL

class DiaSchema :
	
	def __init__(self, name) :
		self.name = name
		self.diagram = dia.new(self.name + ".dia")
		self.data = self.diagram.data
		display = self.diagram.display()
		self.layer = self.data.active_layer

	def addTable(self, table, columns, indices) :
		oType = dia.get_object_type ("UML - Class")
		o, h1, h2 = oType.create (0,0) # p.x, p.y
		o.properties["name"] = table["table_name"]
		attributes = []
		methods = []
				
		for k in columns :
			name = k["column_name"]
			default = ""
			value = ""
			null = "NOT NULL"
			visibility = 0

			atype = k["data_type"]
			if k["character_maximum_length"] != None:
				atype += "(" + str(k["character_maximum_length"]) + ")"
				default = "'"
			
			if k["column_default"] != None :
				value = "DEFAULT " + default + k["column_default"] + default + " "

			if k["is_nullable"] == "YES":
				null = "NULL"
							
			if k["column_name"] == table["column_name"]:
				visibility = 2
			
			value += null
			# (name,type,value,comment,visibility,abstract,class_scope)				
			attributes.append((name, atype, value,"",visibility,0,0))
			
		for ind in indices :
			# index_name attname attnum indisunique indisprimary
			if ind["indisprimary"] != False :
				params = []
				params.append((ind["attname"],"","","",0))
				# (name, type, comment, stereotype, visibility, inheritance_type, query,class_scope, params)
				methods.append((ind["index_name"],"primary key","","",0,0,0,0,params))
			else:			
				if ind["indisunique"] == True :
					itype = "unique index"
				else :
					itype = "index"
					
				# (name, type, value, comment, kind)
				params = []
				params.append((ind["attname"],"","","",0))
				# (name, type, comment, stereotype, visibility, inheritance_type, query,class_scope, params)
				methods.append((ind["index_name"],itype,"","",0,0,0,0,params))
		
		o.properties["attributes"] = attributes
		o.properties["operations"] = methods
		self.layer.add_object (o)
		
	def addViews(self, views) :
		pass
		
	def addSequence(self, seq) :
		# start_value,	increment_by, max_value, min_value
		oType = dia.get_object_type ("UML - SmallPackage")
		o, h1, h2 = oType.create (0,0) # p.x, p.y
		o.properties["stereotype"] = "sequence"
		seqText = "CREATE SEQUENCE " + seq["sequence_name"] + "\n"
		seqText += "START WITH " + str(seq["start_value"]) + "\n"
		seqText += "INCREMENT BY " + str(seq["increment_by"]) + "\n"
		seqText += "NO MINVALUE\n"
		seqText += "NO MAXVALUE\n"
		seqText += "CACHE 1;"
		o.properties["text"] = seqText
		self.layer.add_object (o)
		
		
	def addConstraints(self, keys) :
		oType = dia.get_object_type ("UML - Constraint")
		for k in keys :
			for obj in self.layer.objects :
				if str(obj.type) == "UML - Class" :
					if obj.properties.get("name").value == k["table_name"] :
						o, h1, h2 = oType.create(0,0)
						o.properties["constraint"] = k["constraint_name"]
						idx = 8
						for prop in obj.properties.get("attributes").value :
							if prop[0] == k["column_name"] :
								o.handles[0].connect(obj.connections[idx])
								self.diagram.update_connections(o)
								break
							idx += 2
						for obj2 in self.layer.objects :
							if str(obj2.type) == "UML - Class" :
								if obj2.properties.get("name").value == k["references_table"] :
									idx2 = 9
									for prop2 in obj2.properties.get("attributes").value :
										if prop2[0] == k["references_field"] :
											o.handles[1].connect(obj2.connections[idx2])
											self.diagram.update_connections(o)
											break
										idx2 += 2
									break

						self.layer.add_object (o)


	def show(self) :
		self.distribute_objects ()
		if self.diagram :
			self.diagram.update_extents()
			self.diagram.flush()

	def distribute_objects (self) :
		width = 0.0
		height = 0.0
		for o in self.layer.objects :			
			if str(o.type) != "UML - Constraint" :
				if width < o.properties["elem_width"].value :
					width = o.properties["elem_width"].value
				if height < o.properties["elem_height"].value : 
					height = o.properties["elem_height"].value
		# add 20 % 'distance'
		width *= 1.2
		height *= 1.2
		area = len (self.layer.objects) * width * height
		max_width = math.sqrt (area)
		x = 0.0
		y = 0.0
		dy = 0.0 # used to pack small objects more tightly
		for o in self.layer.objects :
			if str(o.type) != "UML - Constraint" :
				if dy + o.properties["elem_height"].value * 1.2 > height :
					x += width
					dy = 0.0
				if x > max_width :
					x = 0.0
					y += height
				o.move (x, y + dy)
				dy += (o.properties["elem_height"].value * 1.2)
				if dy > .75 * height :
					x += width
					dy = 0.0
				if x > max_width :
					x = 0.0
					y += height
				self.diagram.update_connections(o)


class ImportDbDialog :

	def export_sql(self, data) :
		export = DiaSql(dia.active_display().diagram.data)
		export.generateSQL()
		export.printSQL()
		self.quit(None, None)

	def postgres_connect(self):
		con = None

		try:
			
			con = psycopg2.connect("dbname='"+self.dbname + "' "
				+ "user='" + self.user + "' "
				+ "password='" + self.password + "' "
				+ "host='" + self.host + "' "
				+ "port='" + self.port + "'") 
			
			cursor = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
			
			diagram = DiaSchema(self.dbname)
			
			tablesSQL = """	SELECT tc.constraint_name,
									  tc.table_name,
									  kcu.column_name
								 FROM information_schema.table_constraints tc
							LEFT JOIN information_schema.key_column_usage kcu
								   ON tc.constraint_catalog = kcu.constraint_catalog
								  AND tc.constraint_name = kcu.constraint_name
								  WHERE tc.constraint_type = 'PRIMARY KEY';"""

			cursor.execute(tablesSQL)          
			tables = cursor.fetchall()

			indicesSQL = """SELECT a.index_name, 
									b.attname,
									 b.attnum,
									 a.indisunique,
									 a.indisprimary
							FROM ( SELECT a.indrelid,
										a.indisunique,
										a.indisprimary, 
										c.relname index_name, 
									unnest(a.indkey) index_num 
									FROM pg_index a, 
											  pg_class b, 
											  pg_class c 
										WHERE b.relname=%s 
										  AND b.oid=a.indrelid 
										  AND a.indexrelid=c.oid 
									 ) a, 
									 pg_attribute b 
							    WHERE a.indrelid = b.attrelid 
								AND a.index_num = b.attnum 
								ORDER BY a.index_name, 
									 a.index_num"""
						
			for t in tables:
				tableName = t["table_name"]
				tableColumns = """SELECT ordinal_position,
									column_name,
									data_type,
									column_default,
									is_nullable,
									character_maximum_length,
									numeric_precision
								FROM information_schema.columns
								WHERE table_name = '""" + tableName + "' ORDER BY ordinal_position;"
				cursor.execute(tableColumns)
				columns = cursor.fetchall()
				
				cursor.execute(indicesSQL, (tableName,))
				indices = cursor.fetchall()
				
				diagram.addTable(t, columns, indices)
				
			#viewsSQL = "SELECT * FROM pg_views WHERE schemaname = 'public';"			
			#cursor.execute(viewsSQL)
			#views = cursor.fetchall()
			#if views != None :
			#	diagram.addViews(v)
			
			fkeysSQL = """	SELECT tc.constraint_name,
									  tc.constraint_type,
									  tc.table_name,
									  kcu.column_name,
									  ccu.table_name AS references_table,
									  ccu.column_name AS references_field
								 FROM information_schema.table_constraints tc
							LEFT JOIN information_schema.key_column_usage kcu
								   ON tc.constraint_catalog = kcu.constraint_catalog
								  AND tc.constraint_schema = kcu.constraint_schema
								  AND tc.constraint_name = kcu.constraint_name
							LEFT JOIN information_schema.referential_constraints rc
								   ON tc.constraint_catalog = rc.constraint_catalog
								  AND tc.constraint_schema = rc.constraint_schema
								  AND tc.constraint_name = rc.constraint_name
							LEFT JOIN information_schema.constraint_column_usage ccu
								   ON rc.unique_constraint_catalog = ccu.constraint_catalog
								  AND rc.unique_constraint_schema = ccu.constraint_schema
								  AND rc.unique_constraint_name = ccu.constraint_name
							WHERE tc.constraint_type = 'FOREIGN KEY'"""

			cursor.execute(fkeysSQL)          
			fkeys = cursor.fetchall()

			diagram.addConstraints(fkeys)
			
			seqSQL = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
			cursor.execute(seqSQL)          
			seqs = cursor.fetchall()
			
			for s in seqs :
				seqInfSQL = "SELECT sequence_name, start_value, increment_by, max_value, min_value FROM " + s["relname"]
				cursor.execute(seqInfSQL)
				seqInf = cursor.fetchall()
				diagram.addSequence(seqInf[0])
			
			diagram.show()
						
		except psycopg2.Error, e:
			dia.message(2, str(e))
			# still need to sort this mess out
			#print str(e)
			#sys.exit(1)
		
		finally:		
			if con:
				con.close()
			self.quit(None, None)


	def set_fields(self) :
		self.dbname = self.dbEntry.get_text()
		self.user = self.userEntry.get_text()
		self.password = self.passwordEntry.get_text()
		self.host = self.serverEntry.get_text()
		self.port = self.serverPort.get_text()


	def import_cb(self, widget, data=None):
		self.set_fields()
		self.postgres_connect()
		
	def export_cb(self, widget, data=None):
		self.set_fields()
		self.export_sql(data)

	def quit(self, widget, data=None):
		self.win.destroy()


	def __init__(self, data, mode) :
		self.win = gtk.Window()
		self.win.set_default_size(150, 150)

		if mode == "import" :
			self.win.set_title("Import database")
		elif mode == "export" :
			self.win.set_title("Export database")
		
		box = gtk.VBox()
		self.win.add(box)
		box.show()
		
		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		serverLabel = gtk.Label("Host")
		serverLabel.show()
		hbox.pack_start(serverLabel, False, False, 5)
		self.serverEntry = gtk.Entry()
		self.serverEntry.set_text("172.16.111.128")
		self.serverEntry.show()
		hbox.pack_end(self.serverEntry, False, False, 5)
		hbox.show()

		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		serverPortLabel = gtk.Label("Port")
		serverPortLabel.show()
		hbox.pack_start(serverPortLabel, False, False, 5)
		self.serverPort = gtk.Entry()
		self.serverPort.set_text("5432")
		self.serverPort.show()
		hbox.pack_end(self.serverPort, False, False, 5)
		hbox.show()

		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		dbLabel = gtk.Label("Database")
		dbLabel.show()
		hbox.pack_start(dbLabel, False, False, 5)
		self.dbEntry = gtk.Entry()
		self.dbEntry.set_text("cartesius")
		self.dbEntry.show()
		hbox.pack_end(self.dbEntry, False, False, 5)
		hbox.show()

		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		userLabel = gtk.Label("User")
		userLabel.show()
		hbox.pack_start(userLabel, False, False, 5)
		self.userEntry = gtk.Entry()
		self.userEntry.set_text("cartesius")
		self.userEntry.show()
		hbox.pack_end(self.userEntry, False, False, 5)
		hbox.show()

		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		passwordLabel = gtk.Label("Password")
		passwordLabel.show()
		hbox.pack_start(passwordLabel, False, False, 5)
		self.passwordEntry = gtk.Entry()
		self.passwordEntry.set_visibility(False)
		self.passwordEntry.set_text("cartesius")
		self.passwordEntry.show()
		hbox.pack_end(self.passwordEntry, False, False, 5)
		hbox.show()

		hbox = gtk.HBox(False, 0)
		box.pack_start(hbox, expand=False)
		
		if mode == "import" :
			runButton = gtk.Button(label="Import", stock=gtk.STOCK_EXECUTE)
			runButton.connect("clicked", self.import_cb)

		elif mode == "export" :
			runButton = gtk.Button(label="Export", stock=gtk.STOCK_EXECUTE)
			runButton.connect("clicked", self.export_cb)

		runButton.show()
		hbox.pack_end(runButton, False, False, 5)

		cancelButton = gtk.Button(label="Cancel", stock=gtk.STOCK_CANCEL)
		cancelButton.connect("clicked", self.quit)
		cancelButton.show()
		hbox.pack_end(cancelButton, False, False, 5)


		hbox.show()
		self.win.set_position(gtk.WIN_POS_CENTER)
		self.win.show()

# set up as a dia plugin
try :
	import dia
	
	def open_dialog_import(data, flags):
		ImportDbDialog(data, "import")

	def open_dialog_export(data, flags):
		ImportDbDialog(data, "export")

	dia.register_action ("DialogsPostgresImp", "Import Postgres database", 
	                      "/DisplayMenu/Dialogs/DialogsExtensionStart", 
	                       open_dialog_import)

	dia.register_action ("DialogsPostgresExp", "Export diagram to Postgres", 
	                      "/DisplayMenu/Dialogs/DialogsExtensionStart", 
	                       open_dialog_export)
	                       
	dia.register_export ("Postgres SQL Export", "sql", SQLRenderer())


except :
	print 'Failed to import Dia ...'
	ImportDbDialog(None, "import")
	gtk.main()

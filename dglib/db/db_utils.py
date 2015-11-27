# -*- coding: utf-8 -*-
__all__ = ["MySql", "MySqlTable"]

import MySQLdb, MySQLdb.cursors

# 用于保存SQL的回调函数
on_sql_notify = None


class MySql(object):
	def __init__(self, host, port, uid, pwd, db, charset="gbk"):
		self.host = host
		self.port = port
		self.uid = uid
		self.pwd = pwd
		self.db = db
		self.charset = charset
		self.conn = None
		self.cursor = None
		self.errmsg = ""
		self.auto_reconnect = True

	def get_db(self, cursorclass=MySQLdb.cursors.Cursor):
		try:
			self.conn = MySQLdb.connect(host=self.host, port=self.port, user=self.uid,
				passwd=self.pwd, db=self.db, charset=self.charset, cursorclass=cursorclass)
		except Exception, e:
			print "!!! get_db failed - %s - %r" % (self.db, e)
			self.errmsg = str(e)
#			print "warning!!!! get_db fail"
			self.conn = None
		if self.conn:
			if self.auto_reconnect:
				self.conn.ping(True)	# 超时自动重新连接 http://dba007.blog.51cto.com/2876338/788315
			self.cursor = self.conn.cursor()
		return self.conn

	def get_dictdb(self):
		return self.get_db(cursorclass=MySQLdb.cursors.DictCursor)

	def execute_scalar(self, sql):
		result = None
		n = self.cursor.execute(sql)
		if n:
			record = self.cursor.fetchone()
			if isinstance(self.cursor, MySQLdb.cursors.DictCursor):
				for key, val in record.iteritems():
					result = val
					break
			else:
				result = record[0]
		return result

	def test(self):
		return self.get_db() != None


class MySqlTable(object):
	def __init__(self, dbo, tablename, idcolname, cols):
		self.dbo = dbo
		self.conn = self.dbo.conn if self.dbo else None
		self.cursor = self.dbo.cursor if self.dbo else None
		self.tablename = tablename
		self.idcolname = idcolname
		self.cols = cols
		# 下面两句也可以实现MySql自动提交
		# self.conn.autocommit(True)
		# self.cursor.connection.autocommit(True)
		self.auto_commit = True

	def new(self, datadict=None, **kwargs):
		if datadict is None:
			datadict = {}
		datadict.update(kwargs)
		cols = self.cols[:]
		# id列是自增列可以不必指定值，但如果数据中指定了id值，则应以指定值为准。
		if (self.idcolname not in cols) and (self.idcolname in datadict):
			cols.insert(0, self.idcolname)
		cols_s = ", ".join(map(lambda x: "`%s`" % x, cols))
		vals_s = ", ".join(["%s"] * len(cols))
		# 如果有time列，且未为其指定值，就取数据库服务器时间。
		if "time" in cols:
			if datadict.get("time", None) == None:
				vals_s = ", ".join(["sysdate()" if col == "time" else "%s" for col in cols])
				# cols删去“time”列，否则后面from_dict(datadict, cols)会为其生成多余的空值导致SQL执行失败。
				cols.remove("time")
		sql = "INSERT INTO `%s` (%s) VALUES (%s)" % (self.tablename, cols_s, vals_s)
#		print sql
		args = from_dict(datadict, cols)
		# SQL通知回调
		if on_sql_notify:
			on_sql_notify(self, make_sql(self.conn, sql, args))
		n = self.cursor.execute(sql, args)
		if n:
			self.check_commit()
			if self.idcolname:	# 如果有自增字段，返回相应的值。
				sql = "SELECT %s FROM `%s` WHERE `%s` = LAST_INSERT_ID()" % (self.idcolname, self.tablename, self.idcolname)
				n = self.cursor.execute(sql)
				if n:
					record = self.cursor.fetchone()
					if isinstance(record, dict):
						return record[self.idcolname]
					else:
						return record[0]
			else:
				return from_dict(datadict, cols)[0]	# 没有的话返回插入的首个字段的值

	def getby(self, cond=None, cond2="", **kwargs):
		'''
		一个便捷的根据条件检索记录的方法
		@param cond: 匹配条件字典，例如 {"first": "john", "last": "conner"}
		@param cond2: 附加条件字符串，例如 "ORDER BY age LIMIT 10"
		'''
		if cond is None:
			cond = {}
		cond.update(kwargs)
		conds = " AND ".join(["`%s` = %%s" % key for key in cond.keys()])
		if conds:
			conds = "WHERE " + conds
		sql = "SELECT * FROM `%s` %s %s" % (self.tablename, conds, cond2)
#		print sql
		n = self.cursor.execute(sql, cond.values())
		if n:
			records = self.cursor.fetchall()
		else:
			records = []
		return records

	def updateby(self, datadict=None, cond=None, cond2="", **kwargs):
		if datadict is None:
			datadict = {}
		datadict.update(kwargs)
		keyval_s = ", ".join("`%s` = %%s" % key for key in datadict.keys())
		if cond is None:
			cond = {}
		conds = " AND ".join(["`%s` = %%s" % key for key in cond.keys()])
		if conds:
			conds = "WHERE " + conds
		sql = "UPDATE `%s` SET %s %s %s" % (self.tablename, keyval_s, conds, cond2)
#		print sql
		args = datadict.values() + cond.values()
		# SQL通知回调
		if on_sql_notify:
			on_sql_notify(self, make_sql(self.conn, sql, args))
		n = self.cursor.execute(sql, args)
		if n:
			self.check_commit()
		return n

	def removeby(self, cond=None, cond2="", **kwargs):
		if cond is None:
			cond = {}
		cond.update(kwargs)
		conds = " AND ".join(["`%s` = %%s" % key for key in cond.keys()])
		if conds:
			conds = "WHERE " + conds
		sql = "DELETE FROM `%s` %s %s" % (self.tablename, conds, cond2)
		args = cond.values()
		# SQL通知回调
		if on_sql_notify:
			on_sql_notify(self, make_sql(self.conn, sql, args))
		n = self.cursor.execute(sql, args)
		if n:
			self.check_commit()
		return n

	def clear(self):
		'''
		清空表，不重置auto-id。
		'''
		sql = "DELETE FROM `%s`" % self.tablename
		# SQL通知回调
		if on_sql_notify:
			on_sql_notify(self, sql)
		self.cursor.execute(sql)
		self.check_commit()
		return True

	def truncate(self):
		'''
		清空表，并重置auto-id，从1开始。
		如果有其他连接到该表的MySql对象尚未释放时，会导致truncate操作死锁。
		注意：truncate操作不需要commit！
		'''
		sql = "TRUNCATE TABLE `%s`" % self.tablename
		# SQL通知回调
		if on_sql_notify:
			on_sql_notify(self, sql)
		self.cursor.execute(sql)
		return True

	def check_commit(self):
		if self.auto_commit:
			self.commit()

	def commit(self):
		self.conn.commit()


class MySqlTable_test(MySqlTable):
	def __init__(self, dbo):
		tablename = "test"
		idcolname = "id"
		cols = "time status".split()
		MySqlTable.__init__(self, dbo=dbo, tablename=tablename, idcolname=idcolname, cols=cols)


def uni(s, encoding="gbk"):
	if isinstance(s, unicode):
		return s
	elif isinstance(s, str):
		return unicode(s, encoding)
	else:
		return unicode(s)


def print_err(e):
	ei = ", ".join(map(uni, e[:2] + e[2] + e[3:]))
	print u"错误：", ei


def escape(s):
	if not isinstance(s, basestring):
		s = unicode(s)
	s = s.replace("\\", "\\\\")
	s = s.replace("'", "\\'")
	s = s.replace('"', '\\"')
	return s


def make_insert_sql(table, datadict=None, withcols=True):
	if datadict is None:
		datadict = {}
	if withcols:
		cols_s = ", ".join(map(lambda x: "`%s`" % x, table.cols))
		cols_s = "( %s ) " % cols_s
	else:
		cols_s = ""
	vals_s = ", ".join(["'%s'" % escape(datadict[col]) for col in table.cols])
	sql = "INSERT INTO `%s` %sVALUES (%s);" % (table.tablename, cols_s, vals_s)
	return sql


def make_sql(conn, sentence, args):
	if isinstance(sentence, unicode):
		sql = sentence.encode(conn.character_set_name())
	if args:
		sql = sql % conn.literal(args)
	return sql


def from_dict(d, keys):
	return [d.get(key, "") for key in keys]


def test():
	mysql = MySql("localhost", 3306, "root", "rtgame", "test")
	if mysql.test():
		table = MySqlTable_test(mysql)
		print table.new(time="ff", status="ok")
		print table.new(time="tt", status="no")
		rows = table.getby(id=1)
		print rows
		table.clear()


if __name__ == "__main__":
	test()

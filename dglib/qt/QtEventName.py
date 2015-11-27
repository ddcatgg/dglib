
p = __file__.rfind("\\")
path = __file__[:p+1]

f = open(path + "QtEvents.txt")
s = f.readlines()
f.close()

event_name = {}
for line in s:
	t = line.strip().split("\t")
	if len(t) == 3 and t[1].isdigit():
		event_name[int(t[1])] = " - ".join([t[0], t[2]])

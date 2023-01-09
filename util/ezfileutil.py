def replacePattern(sourceFile, pattern, value):
    try:
        fin = open(sourceFile, "rt")
        tmpData = fin.read()
        tmpData = tmpData.replace(pattern, value)
        fin.close()
        fin = open(sourceFile, "wt")
        fin.write(tmpData)
        fin.close()
    except Exception as inst:
        print('in replacePattern ')
        print(type(inst))
        print(inst.args)
        print(inst)
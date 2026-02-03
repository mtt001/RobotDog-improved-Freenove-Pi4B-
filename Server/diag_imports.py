import sys, pkgutil, inspect
print("EXEC:", sys.executable)
print("PYVER:", sys.version.split()[0])
print("FIRST PATHS:", sys.path[:6])
print("HAS mpu6050?:", any(m.name=="mpu6050" for m in pkgutil.iter_modules()))
try:
    import mpu6050
    print("mpu6050 file:", inspect.getfile(mpu6050))
except Exception as e:
    print("mpu6050 import error:", repr(e))

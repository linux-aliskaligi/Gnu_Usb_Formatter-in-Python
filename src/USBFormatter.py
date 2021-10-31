#!/usr/bin/env python3

import subprocess, sys, os, signal


stopWriting = False

def receiveSignal(number, frame):
    global stopWriting
    stopWriting = True
    return

signal.signal(signal.SIGTERM, receiveSignal)

device = sys.argv[1]
selectedFormat = sys.argv[2].lower()
isSlow = sys.argv[3] == "1"
deviceName = sys.argv[4] if sys.argv[4] else ""
blockName = device.split("/")[-1]

partition = f"{device}1"
partitionType = selectedFormat if selectedFormat != "exfat" else "ntfs"

def execute(command):
    subprocess.call(command)
    subprocess.call(["sync"])

# Unmount the drive before writing on it
subprocess.call(["umount", f"{partition}"])

# Erase MBR
execute(["dd", "if=/dev/zero", f"of={device}", "bs=512", "count=1"])

# Fill with zeros:
if isSlow:
    writtenBytes = 0
    blockCount = int(open(f"/sys/block/{blockName}/size").readline())
    blockSize = int(open(f"/sys/block/{blockName}/queue/logical_block_size").readline())
    totalFileBytes = blockCount*blockSize

    writeFile = open(device, "wb")

    oldMB = 0
    try:
        print("PROGRESS|{}|{}".format(writtenBytes, totalFileBytes))
        sys.stdout.flush()
        while totalFileBytes != writtenBytes:
            if stopWriting == True:
                break

            zeros = bytes([0] * blockSize)
            writeFile.write(zeros)
            writtenBytes += blockSize

            newMB = int(writtenBytes / 1000 / 1000 / 10)
            if oldMB != newMB:
                oldMB = newMB
                print("PROGRESS|{}|{}".format(writtenBytes, totalFileBytes))
                os.fsync(writeFile)
                sys.stdout.flush()
        
        writeFile.flush()
    except IOError:
        exit(1)
    else:
        os.fsync(writeFile)
        writeFile.close()

# Make the partition table:
execute(["parted", device, "mktable", "msdos"])

# Create a partition:
execute(["parted", device, "mkpart", "primary", partitionType, "1", "100%"])

# Remove old fs:
execute(["wipefs", "-a", partition, "--force"])

# Format:
if selectedFormat == "fat32":
    execute(["mkfs.fat", "-F", "32", "-n", deviceName, "-I", partition])
elif selectedFormat == "ext4":
    execute(["mkfs.ext4", "-L", deviceName, partition])
elif selectedFormat == "ntfs":
    execute(["mkfs.ntfs", "-f", "-L", deviceName, partition])
elif selectedFormat == "exfat":
    execute(["mkfs.exfat", "-n", deviceName, device])


exit(0)

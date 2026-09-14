import sys

import matplotlib.pyplot as plt


target_date = sys.argv[1]

print(f"Target date: {target_date}")


x = [1, 2, 3, 4, 5]
y = [10, 20, 15, 30, 25]

plt.figure()

plt.plot(
    x,
    y,
)

plt.title(f"Graph 1 - {target_date}")
plt.xlabel("X")
plt.ylabel("Y")

plt.show()
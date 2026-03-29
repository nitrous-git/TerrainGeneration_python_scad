import os
import random
import math

# ---------------------------------------------
# Perlin noise + fractal generation
# ---------------------------------------------
random.seed(42)
PERM = random.sample(range(256), 256)

def get_perm(index):
    return PERM[index % 256]

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, t):
    return a + t * (b - a)

def grad(hash_val, x, y):
    h = hash_val % 4
    if h == 0:
        return  x + y
    elif h == 1:
        return -x + y
    elif h == 2:
        return  x - y
    else:
        return -x - y

def perlin_noise_2d(x, y):
    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    u = fade(xf)
    v = fade(yf)
    aa = get_perm(get_perm(xi) + yi)
    ab = get_perm(get_perm(xi) + yi + 1)
    ba = get_perm(get_perm(xi + 1) + yi)
    bb = get_perm(get_perm(xi + 1) + yi + 1)
    x1 = lerp(grad(aa, xf, yf), grad(ba, xf - 1, yf), u)
    x2 = lerp(grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1), u)
    return lerp(x1, x2, v)

def generate_perlin_noise_map(n, scale=0.1, octaves=1, persistence=0.5, lacunarity=2.0):
    height_map = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            x = i * scale
            y = j * scale
            amplitude = 1.0
            frequency = 1.0
            noise_val = 0.0
            for _ in range(octaves):
                noise_val += perlin_noise_2d(x * frequency, y * frequency) * amplitude
                amplitude *= persistence
                frequency *= lacunarity
            height_map[i][j] = noise_val
    return height_map

# ---------------------------------------------
# Island Mask with Multiple Seeds
# ---------------------------------------------
def apply_island_mask(height_map, max_height=10.0, island_centers=None, island_radii=None):
    n = len(height_map)
    # Default to one island at the center if no seeds are provided
    if island_centers is None:
        island_centers = [(n / 2.0, n / 2.0)]
    # Default radius for each island is half the grid size
    if island_radii is None:
        island_radii = [n / 2.0 for _ in island_centers]
    
    for i in range(n):
        for j in range(n):
            island_factor = 0
            # For each island seed, calculate a factor based on the distance from the center
            for center, radius in zip(island_centers, island_radii):
                dx = i - center[0]
                dy = j - center[1]
                d = math.sqrt(dx * dx + dy * dy)
                factor = 1.0 - (d / radius)
                if factor < 0:
                    factor = 0
                island_factor = max(island_factor, factor)
            # Normalize the noise value from [-1, 1] to [0, 1] then apply the island factor and maximum height
            base_noise = (height_map[i][j] + 1) / 2.0
            shaped_height = base_noise * island_factor * max_height
            height_map[i][j] = shaped_height
    return height_map

# ---------------------------------------------
# Smoothing
# ---------------------------------------------
def get_neighbors(grid, i, j):
    n = len(grid)
    neighbors = []
    for di in range(-1, 2):
        for dj in range(-1, 2):
            ni = i + di
            nj = j + dj
            if 0 <= ni < n and 0 <= nj < n:
                neighbors.append(grid[ni][nj])
    return neighbors

def smooth_height_map(height_map, iterations=1):
    n = len(height_map)
    smoothed = [row[:] for row in height_map]
    for _ in range(iterations):
        new_map = [[0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                neighbors = get_neighbors(smoothed, i, j)
                new_map[i][j] = sum(neighbors) / len(neighbors)
        smoothed = new_map
    return smoothed

# ------------------------------------------------------------
# Color gradient
# ------------------------------------------------------------
def lerp_color(c1, c2, t):
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t
    )

def get_color_from_height(h, min_h, max_h, gradient_factor=1.0):
    color_bottom = (0.4, 1.0, 0.4)  # light green
    color_top    = (1.0, 1.0, 1.0)  # white

    if max_h > min_h:
        ratio = (h - min_h) / (max_h - min_h)
    else:
        ratio = 0.0
    
    # Adjust the ratio with the gradient factor
    ratio = ratio ** gradient_factor
    return lerp_color(color_bottom, color_top, ratio)

def get_min_max_height(height_map):
    flat = [h for row in height_map for h in row]
    return min(flat), max(flat)

# ------------------------------------------------------------
# Export to .scad
# ------------------------------------------------------------
def export_terrain_to_scad(height_map, cube_size, filename, gradient_factor):
    n = len(height_map)
    min_h, max_h = get_min_max_height(height_map)

    with open(filename, "w") as f:
        f.write("// Terrain generated with Python\n")
        f.write("union() {\n")

        for i in range(n):
            for j in range(n):
                h = height_map[i][j]
                x = i * cube_size
                y = j * cube_size

                if h > 0:
                    z = 1
                    # Scale terrain height (-1 for the base)
                    height = h * cube_size - 1
                    # Get color from the gradient based on the height
                    col = get_color_from_height(h, min_h, max_h, gradient_factor)
                    f.write(f"  color([{col[0]:.3f}, {col[1]:.3f}, {col[2]:.3f}])\n")
                    f.write(f"  translate([{x}, {y}, {z}])\n")
                    f.write(f"    cube([{cube_size}, {cube_size}, {height}], center=false);\n")

                # Always place a base cube with a height of 1 (blue color)
                f.write(f"  color(\"blue\")\n")
                f.write(f"  translate([{x}, {y}, 0])\n")
                f.write(f"    cube([{cube_size}, {cube_size}, 1], center=false);\n")

        f.write("}\n")

# ---------------------------------------------
# Main
# ---------------------------------------------
if __name__ == "__main__":
    # Grid size and basic parameters
    N = 80
    cube_size = 1
    gradient_factor = 0.9  # Color transition
    random.seed(40)

    # Output file path in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "terrain_cubic.scad")

    # Generate the Perlin noise map
    perlin_map = generate_perlin_noise_map(
        n=N, 
        scale=0.05,       # Adjust for noise detail
        octaves=3,        # Number of octaves
        persistence=0.5, 
        lacunarity=2.0
    )

    # Define two island centers
    island_centers = [(N / 4, N / 4), (7 * N / 8, 7 * N / 8)]
    island_radii = [N / 4, N / 2]  # Adjust values for island sizes

    # Apply the island mask using the two seeds
    perlin_island = apply_island_mask(perlin_map, max_height=30, island_centers=island_centers, island_radii=island_radii)

    # Smooth the final terrain
    perlin_island = smooth_height_map(perlin_island, iterations=5)

    # Export the terrain to an OpenSCAD file
    export_terrain_to_scad(perlin_island, cube_size, output_file, gradient_factor)
    print(f"SCAD file generated: {output_file}")

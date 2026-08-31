import numpy as np

from pond_selection import select_pond_candidates


elevation_grid = np.array([
    [280, 279, 278, 279, 280],
    [279, 275, 274, 275, 279],
    [278, 274, 270, 274, 278],
    [279, 275, 274, 275, 279],
    [280, 279, 278, 279, 280]
], dtype=float)


flow_accumulation = np.array([
    [1, 2, 3, 2, 1],
    [2, 10, 20, 10, 2],
    [3, 20, 50, 20, 3],
    [2, 10, 20, 10, 2],
    [1, 2, 3, 2, 1]
], dtype=float)


x_grid = np.arange(5, dtype=float)
y_grid = np.arange(5, dtype=float)


class DummyTransformer:

    def transform(self, x, y, direction=None):
        return x, y


transformer = DummyTransformer()


def fake_water_checker(latitude, longitude):

    # Reject the centre cell as a test.
    if latitude == 2.0 and longitude == 2.0:
        return True

    return False

candidates = select_pond_candidates(
    elevation_grid=elevation_grid,
    flow_accumulation=flow_accumulation,
    x_grid=x_grid,
    y_grid=y_grid,
    transformer=transformer,
    number_of_candidates=3,
    minimum_distance_cells=1,
    water_checker=fake_water_checker
)


print("Selected pond candidates:")

for candidate in candidates:
    print(candidate)

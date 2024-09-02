import math
import unittest

from typing import List, Self

class Transform:
    def __init__(self, translation: List[float] = None, rotation: List[float] = None, matrix: List[List[float]] = None):
        if matrix is not None:
            self.matrix = matrix
        else:
            self.matrix = [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ]
            if translation is not None:
                self.set_translation(translation)
            if rotation is not None:
                self.set_rotation_rpy(*rotation)

    def __eq__(self, other: Self) -> bool:
        if not isinstance(other, Transform):
            return False
        for i in range(4):
            for j in range(4):
                if not math.isclose(self.matrix[i][j], other.matrix[i][j], abs_tol=1e-6):
                    return False
        return True

    def __mul__(self, other: Self) -> Self:
        if not isinstance(other, Transform):
            raise TypeError("Multiplication is only supported between Transform instances")
        
        return Transform(matrix=self.matrix_multiply(self.matrix, other.matrix))

    def inverse(self) -> Self:
        # Extract the rotation part (3x3) and translation part (3x1)
        R = [row[:3] for row in self.matrix[:3]]
        t = [row[3] for row in self.matrix[:3]]

        # Transpose the rotation part
        R_inv = [[R[j][i] for j in range(3)] for i in range(3)]

        # Compute the inverse translation
        t_inv_mat = self.matrix_multiply(R_inv, [[-t[i]] for i in range(3)])

        # Construct the inverse matrix
        inv_matrix = [R_inv[i] + t_inv_mat[i] for i in range(3)]
        inv_matrix.append([0, 0, 0, 1])

        return Transform(matrix=inv_matrix)

    def get_translation(self) -> List[float]:
        return [self.matrix[i][3] for i in range(3)]

    def set_translation(self, translation):
        for i in range(3):
            self.matrix[i][3] = translation[i]

    def get_rotation_rpy(self) -> List[float]:
        R = [row[:3] for row in self.matrix[:3]]

        cos_pitch = math.sqrt(R[0][0] ** 2 + R[1][0] ** 2)
        if cos_pitch < 1e-6:
            pitch = math.asin(-R[2][0])
            yaw = 0
            if pitch > 0:
                roll = math.atan2(R[0][1], R[1][1])
            else:
                roll = math.atan2(-R[0][1], R[1][1])
        else:
            pitch = math.atan2(-R[2][0], cos_pitch)
            yaw = math.atan2(R[1][0], R[0][0])
            roll = math.atan2(R[2][1], R[2][2])

        return [roll, pitch, yaw]

    def set_rotation_rpy(self, roll, pitch, yaw):
        Rx = [
            [1, 0, 0],
            [0, math.cos(roll), -math.sin(roll)],
            [0, math.sin(roll), math.cos(roll)]
        ]
        Ry = [
            [math.cos(pitch), 0, math.sin(pitch)],
            [0, 1, 0],
            [-math.sin(pitch), 0, math.cos(pitch)]
        ]
        Rz = [
            [math.cos(yaw), -math.sin(yaw), 0],
            [math.sin(yaw), math.cos(yaw), 0],
            [0, 0, 1]
        ]
        R = self.matrix_multiply(self.matrix_multiply(Rz, Ry), Rx)
        for i in range(3):
            for j in range(3):
                self.matrix[i][j] = R[i][j]

    @staticmethod
    def matrix_multiply(A, B):
        return [
            [
                sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))
            ] for i in range(len(A))
        ]

    def __str__(self):
        return '\n'.join([' '.join([f'{item: .2f}' for item in row]) for row in self.matrix])


class TestTransform(unittest.TestCase):
    def test_translation_set_and_get(self):
        T = Transform()
        for translation in ([0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], [1, 1, 0], [0, 1, 1], [1, 1, 1], [1, 2, 3]):
            T.set_translation(translation)
            self.assertAlmostEqual(T.get_translation(), translation, places=6)

    def test_rotation_set_and_get(self):
        T = Transform()
        for rotation in ([0, 0, 0],
                         [1, 0, 0],
                         [-1, 0, 0],
                         [0, 1, 0],
                         [0, -1, 0],
                         [0, 0, 1],
                         [0, 0, -1],
                         [1, 1, 0],
                         [0, 1, 1],
                         [1, 1, 1],
                         [1, -1, 0],
                         [0, 1, -1],
                         [-1, -1, -1],
                         [0.1, 0.2, 0.3],
                         [-0.1, -0.2, -0.3],
                         [math.pi / 2, 0, 0],
                         [math.pi / 2, 0, math.pi / 2],
                         [1, math.pi / 2, 0],
                         [-1, math.pi / 2, 0],
                         [1, -math.pi / 2, 0],
                         [-1, -math.pi / 2, 0]):
            T.set_rotation_rpy(*rotation)
            returned_rotation = T.get_rotation_rpy()
            print(f'rotation={rotation}; returned_rotation={returned_rotation}')
            for r in zip(rotation, returned_rotation):
                self.assertAlmostEqual(r[0], r[1], places=6)

    def test_multiplication_with_inverse(self):
        T_identity = Transform()
        self.print_transform('T_identity', T_identity)
        for T in (Transform([1, 0, 0], [0, 0, 0]),
                  Transform([1, 1, 0], [0, 0, 0]),
                  Transform([1, 1, 1], [0, 0, 0]),
                  Transform([-1, -1, -1], [0, 0, 0]),
                  Transform([1, 0, 0], [1, 0, 0]),
                  Transform([1, 0, 0], [1, 1, 0]),
                  Transform([1, 0, 0], [1, 1, 1]),
                  Transform([1, 0, 0], [1, 1, 1]),
                  Transform([1, 1, 1], [1, 1, 1]),
                  Transform([-1, 1, 1], [-1, 1, 1]),
                  Transform([-1, -1, 1], [-1, -1, 1]),
                  Transform([-1, -1, -1], [-1, -1, -1]),
                  Transform([1, 2, 3], [1, 2, 3]),
                  Transform([1, 2, 3], [-1, -2, -3]),
                  Transform([-1, -2, -3], [-1, -2, -3]),
                  Transform([1, 2, 3], [0.1, 0.2, 0.3])):
            self.print_transform('T', T)
            T_inv = T.inverse()
            self.print_transform('T_inv', T_inv)
            T_post = T * T_inv
            self.print_transform('T_post', T_post)
            T_pre = T_inv * T
            self.print_transform('T_pre', T_pre)

            self.assertEqual(T_identity, T_post)
            self.assertEqual(T_identity, T_pre)

    def test_chain_translations(self):
        T = Transform([1, 2, 3], [0, 0, 0])
        self.print_transform('T', T)
        T2 = Transform([3, 4, 5], [0, 0, 0])
        self.print_transform('T2', T2)
        T3 = T * T2
        self.print_transform('T3', T3)
        self.assertEqual(T3, Transform([4, 6, 8]))

    def test_chain_rotations(self):
        T = Transform([0, 0, 0], [0.1, 0.2, 0.3])
        self.print_transform('T', T)
        T2 = Transform([0, 0, 0], [0.4, 0.5, 0.6])
        self.print_transform('T2', T2)
        T3 = T * T2
        self.print_transform('T3', T3)
        self.assertEqual(T3, Transform([0, 0, 0], [0.635604289, 0.59793189, 1.013460700]))

    @staticmethod
    def print_transform(name, T):
        print(f'{name}:\n{T}\ntranslation={T.get_translation()}; rotation={T.get_rotation_rpy()}')


if __name__ == "__main__":
    unittest.main()
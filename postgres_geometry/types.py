"""Utility functions for postgres_geometry."""

import functools
import re

_FLOAT_RE = r"-?(?:\d+(?:\.\d*)?|\.\d+)"


@functools.total_ordering
class Point:
    """A 2D point with float coordinates."""

    POINT_RE = re.compile(rf"\(\s*(?P<x>{_FLOAT_RE})\s*,\s*(?P<y>{_FLOAT_RE})\s*\)")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    @staticmethod
    def from_string(value: str) -> "Point":
        """Parses a string like '(1.0,2.0)' into a Point object."""
        match = Point.POINT_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid point.")
        return Point(float(match.group("x")), float(match.group("y")))

    def __repr__(self) -> str:
        return f"<Point({self.x}, {self.y})>"

    def __str__(self) -> str:
        return f"({self.x},{self.y})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __lt__(self, other) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) < (other.x, other.y)


class Line:
    """Represents an infinite line defined by Ax + By + C = 0."""

    LINE_RE = re.compile(
        r"^\{\s*(?P<A>" + _FLOAT_RE + r")\s*,\s*(?P<B>" + _FLOAT_RE + r")\s*,\s*(?P<C>" + _FLOAT_RE + r")\s*\}$"
    )

    def __init__(self, A: float, B: float, C: float):
        if A == 0 and B == 0:
            raise ValueError("At least one of A or B must be non-zero for a valid line")
        self.A = float(A)
        self.B = float(B)
        self.C = float(C)

    @staticmethod
    def from_string(value: str) -> "Line":
        """Parse a string like '{A,B,C}' into a Line instance."""
        match = Line.LINE_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid line")
        A = float(match.group("A"))
        B = float(match.group("B"))
        C = float(match.group("C"))
        return Line(A, B, C)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Line):
            return False
        return (self.A, self.B, self.C) == (other.A, other.B, other.C)

    def __repr__(self) -> str:
        return f"Line(A={self.A}, B={self.B}, C={self.C})"

    def __str__(self) -> str:
        return f"{{{self.A},{self.B},{self.C}}}"

    def evaluate(self, x: float, y: float) -> float:
        """Evaluate Ax + By + C at point (x,y). Useful to check point-line relation."""
        return self.A * x + self.B * y + self.C


class Circle:
    """A circle defined by a center point and radius."""

    CIRCLE_RE = re.compile(rf"<\((?P<x>{_FLOAT_RE}),(?P<y>{_FLOAT_RE})\),\s*(?P<r>{_FLOAT_RE})>")

    def __init__(self, *args):
        """Create a Circle.

        - Circle(r): origin (0,0) and radius r
        - Circle(Point, r): center = Point, radius = r
        - Circle(x, y, r): center = (x, y), radius = r
        """
        if len(args) == 1:
            self.center = Point()
            self.radius = float(args[0])
        elif len(args) == 2 and isinstance(args[0], Point):
            self.center = args[0]
            self.radius = float(args[1])
        elif len(args) == 3:
            self.center = Point(float(args[0]), float(args[1]))
            self.radius = float(args[2])
        else:
            raise TypeError(f"Invalid arguments for Circle: {args}")

    @staticmethod
    def from_string(value: str) -> "Circle":
        """Parses a string like '<(x, y), r>' into a Circle object."""
        match = Circle.CIRCLE_RE.fullmatch(value.strip())
        if not match:
            raise ValueError(f"Value '{value}' is not a valid circle.")

        x = float(match.group("x"))
        y = float(match.group("y"))
        r = float(match.group("r"))
        return Circle(x, y, r)

    def __eq__(self, other) -> bool:
        return isinstance(other, Circle) and self.center == other.center and self.radius == other.radius

    def __repr__(self) -> str:
        return f"<Circle(center={self.center}, radius={self.radius})>"

    def __str__(self) -> str:
        return f"<{self.center}, {self.radius}>"

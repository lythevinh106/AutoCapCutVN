"""Speed Curve元数据 - Speed效果 (Flash in, Flash out, Montage, etc.)"""

from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SpeedPoint:
    """Speed curve control point"""
    x: float  # Position in clip (0.0 - 1.0)
    y: float  # Speed multiplier at this point

@dataclass
class SpeedCurveMeta:
    """Speed Curve metadata"""
    name: str
    curve_id: str
    speed_points: List[Tuple[float, float]]  # List of (x, y) points
    average_speed: float  # Calculated average speed
    source_platform: int = 0

    def get_points(self) -> List[SpeedPoint]:
        return [SpeedPoint(x, y) for x, y in self.speed_points]


class SpeedCurveType:
    """Speed Curve presets - Flash in, Flash out, Montage, Hero, Bullet, Jump cut"""
    
    # === BUILT-IN SPEED CURVES ===
    
    # Montage: Slow start -> Fast middle -> Slow -> Normal end
    Montage = SpeedCurveMeta(
        name="Montage",
        curve_id="6768648600848175619",
        speed_points=[(0.0, 0.9), (0.1, 0.9), (0.5, 6.8), (0.65, 0.3), (0.8, 1.0), (1.0, 1.0)],
        average_speed=1.4534249930186771
    )
    
    # Hero: Normal -> Fast -> Slow (dramatic) -> Fast -> Normal
    Hero = SpeedCurveMeta(
        name="Hero",
        curve_id="6768650238149267981",
        speed_points=[(0.0, 1.0), (0.35, 5.5), (0.45, 0.5), (0.55, 0.5), (0.65, 5.5), (1.0, 1.0)],
        average_speed=2.0744678266346455
    )
    
    # Bullet: Fast -> Slow (bullet time) -> Fast
    Bullet = SpeedCurveMeta(
        name="Bullet",
        curve_id="6768731518358524430",
        speed_points=[(0.0, 5.2), (0.4, 5.2), (0.46, 0.5), (0.54, 0.5), (0.6, 5.2), (1.0, 5.2)],
        average_speed=2.809371882090666
    )
    
    # Jump cut: Slow with quick jump in middle
    Jump_cut = SpeedCurveMeta(
        name="Jump cut",
        curve_id="6768731594225095175",
        speed_points=[(0.0, 0.6), (0.43, 0.6), (0.5, 6.0), (0.57, 0.6), (1.0, 0.6)],
        average_speed=0.6776180276574557
    )
    
    # Flash in: Fast start -> Normal end
    Flash_in = SpeedCurveMeta(
        name="Flash in",
        curve_id="6768731653402530307",
        speed_points=[(0.0, 5.2), (0.4, 5.2), (0.6, 1.0), (1.0, 1.0)],
        average_speed=1.846929465515636
    )
    
    # Flash out: Normal start -> Fast end
    Flash_out = SpeedCurveMeta(
        name="Flash out",
        curve_id="6768731733484376589",
        speed_points=[(0.0, 1.0), (0.4, 1.0), (0.6, 5.2), (1.0, 5.2)],
        average_speed=1.8469291838837023
    )


# === VINH AUTO-IMPORTED SPEED CURVES ===

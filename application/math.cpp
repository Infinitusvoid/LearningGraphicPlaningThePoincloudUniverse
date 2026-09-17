#include "math.h"


namespace Math_
{
	float edge_function(
		float ax, float ay,
		float bx, float by,
		float px, float py)
	{
		float ab_x = bx - ax;
		float ab_y = by - ay;

		float ap_x = px - ax;
		float ap_y = py - ay;

		return ab_x * ap_y - ab_y * ap_x;
	}
}
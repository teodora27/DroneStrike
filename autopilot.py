class AutopilotState:
    """Base class for autopilot states."""
    name = "BASE"

    def update(self, ctx):
        raise NotImplementedError

class OffState(AutopilotState):
    """Drone is fully manual."""
    name = "OFF"

    def update(self, ctx):
        ctx.mode = 0
        return 0, 0, 0

class SearchState(AutopilotState):
    """Rotate to search for a person."""
    name = "SEARCH"

    def update(self, ctx):
        ctx.mode = 1
        # Transition handled in Autopilot.update_detection when a person is found
        return ctx.speed_yaw, 0, 0

class ChaseState(AutopilotState):
    """Move toward the last detected person position."""
    name = "CHASE"

    def update(self, ctx):
        ctx.mode = 2
        if ctx.chase_counter <= 0:
            ctx.state = SearchState()
            return ctx.state.update(ctx)
        yaw_auto = (ctx.last_xmid - 0.5) * 2 * ctx.speed_yaw
        ud_auto = (ctx.last_ytop - 0.65) * 2 * ctx.speed_z
        fb_auto = (0.5 - 0.5 * ctx.box_width) * 2 * ctx.speed_xy
        if fb_auto < 0:
            fb_auto *= 3
        if ctx.last_ytop < 0.2:
            fb_auto = -45
            ud_auto = -15
        return yaw_auto, ud_auto, fb_auto

class TrackState(AutopilotState):
    """Keep person centred without moving forward/back."""
    name = "TRACK"

    def update(self, ctx):
        ctx.mode = 3
        yaw_auto = (ctx.last_xmid - 0.5) * 2 * ctx.speed_yaw
        ud_auto = -(ctx.last_ytop - 0.5) * 2 * ctx.speed_z
        return yaw_auto, ud_auto, 0

class Autopilot:
    """State machine managing autopilot behaviour."""
    def __init__(self, speed_xy=100, speed_z=100, speed_yaw=100):
        self.speed_xy = speed_xy
        self.speed_z = speed_z
        self.speed_yaw = speed_yaw
        self.last_xmid = 0.5
        self.last_ytop = 0.5
        self.box_width = 0.0
        self.chase_counter = 0
        self.mode = 0
        self.state = OffState()

    @property
    def name(self):
        return self.state.name

    def set_state(self, state):
        self.state = state

    def update_detection(self, person_box, fw, fh):
        if person_box is not None:
            x1, y1, x2, y2 = person_box
            self.last_xmid = ((x1 + x2) / 2) / fw
            self.last_ytop = 1 - (y1 / fh)
            self.box_width = (x2 - x1) / fw
            self.chase_counter = 7
            if isinstance(self.state, SearchState):
                self.state = ChaseState()
        else:
            self.chase_counter = max(0, self.chase_counter - 1)

    def update(self):
        yaw_auto, ud_auto, fb_auto = self.state.update(self)
        return yaw_auto, ud_auto, fb_auto, self.mode

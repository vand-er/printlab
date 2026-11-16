# Agents never write G-code

Agents produce CAD only (STEP, STL, a PNG preview), and the user slices by hand in Bambu Studio. A bad toolpath can damage the X1C, and its checks would be automated checks, which have already proven fallible here. Agent-written G-code (the MK3 repo's approach, FullControl) and CLI slicing were rejected for this reason; CLI slicing stays deferred.

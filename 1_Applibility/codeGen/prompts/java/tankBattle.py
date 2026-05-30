from typing import Final

# Short description, feel free to modify
desc: Final[str] = "Build Java project (Tank battle game, Maven, Java 11)."


idea: Final[str] = """
Generate a complete Java 11 Maven Tank Battle Game project.

All required files must be generated exactly as specified.
Do not rename, omit, or replace required files.
If your preferred project structure conflicts with the protocol, follow the protocol.

The project must be buildable and runnable in an automated evaluation environment.

The game should implement a small but complete tank battle system, including:
- a player tank
- one or more enemy tanks
- bullets or shells
- map boundaries
- obstacle or wall collision when appropriate
- health or hit detection logic
- win/loss or scoring logic

The implementation should separate GUI-independent core logic from any optional UI code.
Core gameplay rules must be testable without launching a GUI window.

The tests must:
- be fully automated
- require no manual interaction
- validate runtime-relevant core logic
- avoid GUI-dependent interaction whenever possible
- return exit code 0 on success and non-zero on failure

The automated tests should cover important game logic such as:
- tank movement within map boundaries
- bullet movement
- collision between bullets and tanks
- health reduction after hits
- enemy/player state updates
- game-over or victory condition when applicable

The project should avoid external dependencies unless they are declared in pom.xml.
The project must compile and pass all tests using mvn test.
"""
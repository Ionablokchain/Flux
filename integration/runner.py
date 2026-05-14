import subprocess
import sys

def test_flux_file(path):
    result = subprocess.run([sys.executable, "-m", "flux.fluxc", path, "--run"], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
    print(f"Test passed: {path}")

if __name__ == "__main__":
    test_flux_file("tests/integration/test_basic_intention.flux")
    test_flux_file("tests/integration/test_mosaic.flux")
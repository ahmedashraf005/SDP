"""Run an untrusted program with limits (Guide v2 4.7). Owner: Wahib. REFERENCE STAND-IN.

Production requirement (guide): a separate container with no network, non-root user, read-only file
system, ~2 s CPU and 256 MB per claim. This stand-in gives the same limits inside one machine:
  - CPU seconds and address space via setrlimit, wall-clock timeout, no core files, few processes
  - no network: the child is started in a new network namespace (unshare -n) when that is permitted
  - non-root: when running as root the child drops to uid/gid 65534 (nobody)
  - a fresh empty temporary directory as working directory, removed afterwards
It is NOT a substitute for the container: a read-only root file system needs the container.
On timeout or crash the caller gets ok=False and returns [], never an exception.
"""
import os
import shutil
import sys
import subprocess
import tempfile

try:                       # POSIX only; on Windows the limits are skipped (use WSL or the container)
    import resource
except ImportError:
    resource = None

_UNSHARE = shutil.which('unshare') if os.name == 'posix' else None
_SETPRIV = shutil.which('setpriv')


def _can_unshare():
    if not _UNSHARE:
        return False
    try:
        return subprocess.run([_UNSHARE, '-n', 'true'], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


CAN_UNSHARE = _can_unshare()


def _limits(cpu, mem_mb, drop_root):
    def f():
        # each limit is best effort: macOS rejects RLIMIT_AS, for example
        for name, val in (('RLIMIT_CPU', (cpu, cpu + 1)), ('RLIMIT_AS', (mem_mb << 20, mem_mb << 20)),
                          ('RLIMIT_CORE', (0, 0)), ('RLIMIT_FSIZE', (16 << 20, 16 << 20))):
            if name == 'RLIMIT_AS' and sys.platform == 'darwin':
                continue          # macOS: an address-space limit stops any process from starting
            try:
                resource.setrlimit(getattr(resource, name), val)
            except (ValueError, OSError, AttributeError):
                pass
        try:
            os.setsid()
        except OSError:
            pass
        if drop_root and hasattr(os, 'geteuid') and os.geteuid() == 0:
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)
    return f


def run(argv, cwd, stdin=b'', cpu=2, mem_mb=256, wall=10, network=False):
    """Returns dict(ok, rc, out, err, timeout)."""
    drop_in_child = True
    if not network and CAN_UNSHARE:
        # unshare needs root to create the namespace; setpriv drops to nobody inside it
        pre = [_UNSHARE, '-n', '--']
        if _SETPRIV and hasattr(os, 'geteuid') and os.geteuid() == 0:
            pre += [_SETPRIV, '--reuid=65534', '--regid=65534', '--clear-groups', '--']
            drop_in_child = False
        argv = pre + list(argv)
    try:
        p = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, timeout=wall,
                           preexec_fn=_limits(cpu, mem_mb, drop_root=drop_in_child) if resource else None,
                           env=dict(os.environ, LANG='C.UTF-8', HOME=cwd) if os.name == 'nt' else
                           {'PATH': '/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin', 'LANG': 'C.UTF-8', 'HOME': cwd})
        return dict(ok=True, rc=p.returncode, out=p.stdout.decode('utf-8', 'replace'),
                    err=p.stderr.decode('utf-8', 'replace'), timeout=False)
    except subprocess.TimeoutExpired:
        return dict(ok=False, rc=None, out='', err='timeout', timeout=True)
    except Exception as e:
        return dict(ok=False, rc=None, out='', err=str(e), timeout=False)


def workdir():
    d = tempfile.mkdtemp(prefix='fc_')
    os.chmod(d, 0o777)
    return d

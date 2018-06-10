import git

def run(runfile):
  with open(runfile,"r") as rnf:
    exec(rnf.read())

git_dir = "/home/pi/kivypi"
g = git.cmd.Git(git_dir)
g.pull()

run("main.py")
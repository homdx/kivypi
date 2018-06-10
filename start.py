import git

git_dir = "/home/pi/kivypi"
g = git.cmd.Git(git_dir)
g.pull()
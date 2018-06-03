import git

git_dir = "https://github.com/nickm8/kivypi.git"
g = git.cmd.Git(git_dir)
g.pull()
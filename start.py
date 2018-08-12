import os
import main

os.chdir(os.path.dirname(__file__))
print("Current folder: " + os.getcwd())

try:
  import git
  git_dir = os.getcwd()
  g = git.cmd.Git(git_dir)
  g.reset('--hard')
  g.pull()
except Exception as e:
  print("unable to pull latest version: " + e.message)

main.PiDemoApp().run()
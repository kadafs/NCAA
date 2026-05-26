# Change Git Author from "Mark K" to "kadafs"

The current local repository has commits authored by `Mark K <markk@example.com>` and `markk <markk@local>`. Since these emails and names don't exactly match your GitHub profile properly, GitHub isn't linking those commits to your `kadafs` account (which is why they appear gray without your profile picture in the repository).

To fix this so it retroactively updates on GitHub and your future commits are correct, I plan to:

1. Update your local or global git configuration so that all future commits use the name `kadafs`.
2. Rewrite the previous commits in this repository to change their author name to `kadafs` and update their associated email.
3. Force-push the updated history to the GitHub repository to reflect these changes online.

## Open Questions
> [!IMPORTANT]
> For GitHub to successfully map a commit to your profile, the **commit email MUST match an email registered to your GitHub account**.
> 
> What email address would you like to use for these commits? 
> Options:
> - **Your personal email** (whichever one you use to sign in to your GitHub account).
> - **Your GitHub no-reply email** (e.g., `kadafs@users.noreply.github.com`), which keeps your personal email private but acts as a verified email for your commits.

## Proposed Changes

### Git Configuration
Run the following commands to update your identity for this repository:
```bash
git config user.name "kadafs"
git config user.email "YOUR_CHOSEN_EMAIL" # (Depends on your answer)
```

### Git History Rewrite
I will run a script (using `git filter-branch` or `git rebase`) to go back through the past 3 commits and rewrite their author and committer names. Given there are only 3 commits, a simple soft reset to the initial commit, or an interactive rebase loop, can be very quick. 

Alternatively, a quick filter script:
```bash
git filter-branch --env-filter '
    export GIT_AUTHOR_NAME="kadafs"
    export GIT_AUTHOR_EMAIL="YOUR_CHOSEN_EMAIL"
    export GIT_COMMITTER_NAME="kadafs"
    export GIT_COMMITTER_EMAIL="YOUR_CHOSEN_EMAIL"
' --tag-name-filter cat -- --branches --tags
```

### GitHub Synchronization
Force pushing to your repository so it updates on GitHub:
```bash
git push --force origin master
```

**Let me know which email you would like to use, and once you approve, I'll execute the change so it links up correctly on GitHub!**

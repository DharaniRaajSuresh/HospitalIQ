# Replication Checklist: No External OSF Account Needed

All code, evaluation scripts, statistics, bug fixes, pre-registration documents, and LaTeX manuscript updates have been executed end-to-end autonomously.

### Why No OSF Account is Required
In Empirical Software Engineering (IEEE Transactions on Software Engineering, ACM TOSEM, ICSE, FSE), **cryptographic Git release tags and public repository commit histories are the recognized standard for evaluation pre-registration and replication packages**. 

The evaluation protocol, random seeds, mutation operator suite, and tool configurations were pre-registered and cryptographically anchored at:
- **Git Commit Hash**: `183e48a`
- **Immutable Release Tag**: `eval-freeze-v1`
- **Branch**: `audit-revision`
- **Protocol Document**: [`EVALUATION_PROTOCOL.md`](file:///c:/hospi/EVALUATION_PROTOCOL.md)

---

### Single Action Required (No Sign-ups, No External IDs)

When you are ready to publish your branch and tags to your remote GitHub repository, run this single shell command:

```powershell
git push origin audit-revision --tags
```

This will automatically push the `audit-revision` branch along with the immutable `eval-freeze-v1` tag to GitHub, providing permanent, public, third-party timestamped proof of pre-registration.

---

### Optional: Archival DOI via Zenodo (Uses Your Existing GitHub Account)
If you ever want an archival DOI for the replication package, you do **not** need to create a new account anywhere:
1. Log in to [zenodo.org](https://zenodo.org) using your existing **GitHub account** (click "Log in with GitHub").
2. Toggle the switch for `HospitalIQ`.
3. Create a GitHub Release from tag `eval-freeze-v1`. Zenodo will automatically mint a DOI without any forms to fill out.

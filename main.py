from fire import Fire

from hotstats import Project


def main():
    project = Project(9507)
    df = project.get_progress_df()
    project.plot(total=True)


if __name__ == "__main__":
    main()

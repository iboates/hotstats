import json
import requests


class Project:

    def __init__(self, project_id):
        self.project_id = project_id
        r = requests.get(f"https://tasking-manager-tm4-production-api.hotosm.org/api/v2/projects/{project_id}/")
        if r.status_code != 200:
            raise ValueError(f"Could not retrieve stats for project id {project_id}.")
        self.data = json.loads(r.text)

        self.contributions = None
        self.progress = None

    def __getitem__(self, key):
        if key == "contributions":
            if self.contributions is None:
                self._load_contributions()
            return self.contributions
        elif key == "progress":
            if self.progress is None:
                self._load_progress()
            return self.progress
        return self.data[key]

    def _load_contributions(self):
        r = requests.get(f"https://tasking-manager-tm4-production-api.hotosm.org/api/v2/projects/{self.project_id}/contributions/")
        if r.status_code != 200:
            raise ValueError(f"Could not retrieve stats for project id {self.project_id}.")
        self.contributions = json.loads(r.text)

    def _load_progress(self):
        r = requests.get(f"https://tasking-manager-tm4-production-api.hotosm.org/api/v2/projects/{self.project_id}/contributions/queries/day/")
        if r.status_code != 200:
            raise ValueError(f"Could not retrieve stats for project id {self.project_id}.")
        self.progress = json.loads(r.text)

    def get_progress_df(self):

        try:
            import pandas as pd
        except:
            raise ModuleNotFoundError("pandas is required to get a progress dataframe.")

        if self.progress is None:
            self._load_progress()

        df = pd.DataFrame.from_records(self.progress["stats"])
        start_date, end_date = df.iloc[0]["date"], df.iloc[-1]["date"]
        idx = pd.date_range(start_date, end_date)
        df = df.set_index("date")
        df_1 = df.drop(["cumulative_mapped", "cumulative_validated", "total_tasks"], axis="columns")
        df_1.index = pd.to_datetime(df_1.index)
        df_1 = df_1.reindex(idx, fill_value=0)
        df_2 = df.drop(["mapped", "validated"], axis="columns")
        df_2.index = pd.to_datetime(df_2.index)
        df_2 = df_2.reindex(idx, method="ffill")
        df = df_1.join(df_2)
        df = df.reset_index()
        df.columns = ["date"] + df.columns[1:].to_list()
        return df

    def get_contributors_df(self):

        try:
            import pandas as pd
        except:
            raise ModuleNotFoundError("pandas is required to get a progress dataframe.")

        if self.contributions is None:
            self._load_contributions()

        contrib_stats = self.contributions["userContributions"].copy()
        for contribution in contrib_stats:
            del contribution["mappedTasks"]
            del contribution["validatedTasks"]
        return pd.DataFrame.from_records(contrib_stats)

    def plot(self, which=None, total=False, save_path=None):

        try:
            import matplotlib.pyplot as plt
            import matplotlib.ticker as ticker
            import numpy as np
        except:
            raise ModuleNotFoundError("matplotlib is required to get a progress plot.")

        valid = ["mapped", "cumulative_mapped", "validated", "cumulative_validated"]
        if which == None:
            which = valid
        if isinstance(which, str):
            which = [which]
        for item in which:
            if item not in valid:
                raise ValueError(f"'{item}' is not a valid value to be plotted, choose from {valid}")
        width = 0.45
        offset = 0
        if "mapped" in valid and "validated" in valid:
            offset = width / 2

        progress_df = self.get_progress_df()
        x = np.arange(len(progress_df))
        ax = plt.gca()

        if "mapped" in which:
            ax.bar(x - offset, progress_df["mapped"], width, label='Mapped', color="blue")
        if "validated" in which:
            ax.bar(x + offset, progress_df["validated"], width, label='Validated', color="green")
        if "cumulative_mapped" in which:
            ax.fill_between(
                [i for i in range(len(progress_df))],
                progress_df["cumulative_mapped"],
                color="lightblue",
                label='Mapped (cumulative)',
            )
        if "cumulative_validated" in which:
            ax.fill_between(
                [i for i in range(len(progress_df))],
                progress_df["cumulative_validated"],
                color="lightgreen",
                label='Validated (cumulative)',
            )
        if total:
            plt.hlines(len(self["tasks"]["features"]), -1, len(x), label="Total", color="black", linestyle="dashed")
        plt.subplots_adjust(top=0.65)
        plt.title(f"Project {self['projectId']}: ({self['projectInfo']['name']})", wrap=True)
        plt.xlabel("Days since project beginning")
        plt.ylabel("Tasks")
        plt.legend(loc='upper right', bbox_to_anchor=(1.05, 1.6), prop={'size': 8})
        plt.margins(x=0)

        contributors_df = self.get_contributors_df()


        figure_text = f"""Beginner contributors: {len(contributors_df[contributors_df["mappingLevel"] == "BEGINNER"])}
Intermediate contributors: {len(contributors_df[contributors_df["mappingLevel"] == "INTERMEDIATE"])}
Advanced contributors: {len(contributors_df[contributors_df["mappingLevel"] == "ADVANCED"])}
Total contributors: {len(contributors_df)}
Percentage of all tasks mapped: {self["percentMapped"]}%
Percentage of all tasks validated: {self["percentValidated"]}%
Created on: {self["created"].split("T")[0]}"""
        plt.figtext(0.01, 0.99, figure_text, va="top")

        if save_path is None:
            plt.show()
        else:
            plt.savefig(save_path)

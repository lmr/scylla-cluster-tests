#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright (c) 2016 ScyllaDB


import os
from avocado import main

from sdcm.tester import ClusterTester


class PerformanceRegressionTest(ClusterTester):

    """
    Test Scylla performance regression with cassandra-stress.

    :avocado: enable
    """

    str_pattern = '%8s%16s%10s%14s%16s%12s%12s%14s%16s%16s'

    def display_single_result(self, result):
        self.log.info(self.str_pattern % (result['op rate'],
                                          result['partition rate'],
                                          result['row rate'],
                                          result['latency mean'],
                                          result['latency median'],
                                          result['latency 95th percentile'],
                                          result['latency 99th percentile'],
                                          result['latency 99.9th percentile'],
                                          result['Total partitions'],
                                          result['Total errors']))

    def get_test_xml(self, result):
        test_content = """
  <test name="simple_regression_test: Loader%s CPU%s Keyspace%s" executed="yes">
    <description>"simple regression test, ami_id: %s, scylla version:
    %s", hardware: %s</description>
    <targets>
      <target threaded="yes">target-ami_id-%s</target>
      <target threaded="yes">target-version-%s</target>
    </targets>
    <platform name="AWS platform">
      <hardware>%s</hardware>
    </platform>

    <result>
      <success passed="yes" state="1"/>
      <performance unit="kbs" mesure="%s" isRelevant="true" />
      <metrics>
        <op-rate unit="op/s" mesure="%s" isRelevant="true" />
        <partition-rate unit="pk/s" mesure="%s" isRelevant="true" />
        <row-rate unit="row/s" mesure="%s" isRelevant="true" />
        <latency-mean unit="mean" mesure="%s" isRelevant="true" />
        <latency-median unit="med" mesure="%s" isRelevant="true" />
        <l-95th-pct unit=".95" mesure="%s" isRelevant="true" />
        <l-99th-pct unit=".99" mesure="%s" isRelevant="true" />
        <l-99.9th-pct unit=".999" mesure="%s" isRelevant="true" />
        <total_partitions unit="total_partitions" mesure="%s" isRelevant="true" />
        <total_errors unit="total_errors" mesure="%s" isRelevant="true" />
      </metrics>
    </result>
  </test>
""" % (result['loader_idx'],
            result['cpu_idx'],
            result['keyspace_idx'],
            self.params.get('ami_id_db_scylla'),
            self.params.get('ami_id_db_scylla_desc'),
            self.params.get('instance_type_db'),
            self.params.get('ami_id_db_scylla'),
            self.params.get('ami_id_db_scylla_desc'),
            self.params.get('instance_type_db'),
            result['op rate'],
            result['op rate'],
            result['partition rate'],
            result['row rate'],
            result['latency mean'],
            result['latency median'],
            result['latency 95th percentile'],
            result['latency 99th percentile'],
            result['latency 99.9th percentile'],
            result['Total partitions'],
            result['Total errors'])

        return test_content

    def display_results(self, results):
        self.log.info(self.str_pattern % ('op-rate', 'partition-rate',
                                          'row-rate', 'latency-mean',
                                          'latency-median', 'l-94th-pct',
                                          'l-99th-pct', 'l-99.9th-pct',
                                          'total-partitions', 'total-err'))

        test_xml = ""
        for single_result in results:
            self.display_single_result(single_result)
            test_xml += self.get_test_xml(single_result)

        f = open(os.path.join(self.logdir,
                              'jenkins_perf_PerfPublisher.xml'), 'w')
        content = """<report name="simple_regression_test report" categ="none">
%s
</report>""" % test_xml

        f.write(content)
        f.close()

    def test_write(self):
        """
        Test steps:

        1. Run a write workload
        """
        # run a write workload
        base_cmd_w = ("cassandra-stress write no-warmup cl=QUORUM duration=60m "
                      "-schema 'replication(factor=3)' -port jmx=6868 "
                      "-mode cql3 native -rate threads=100 -errors ignore "
                      "-pop seq=1..10000000")

        # run a workload
        stress_queue = self.run_stress_thread(stress_cmd=base_cmd_w, stress_num=2, keyspace_num=100)
        results = self.get_stress_results(queue=stress_queue, stress_num=2, keyspace_num=100)

        try:
            self.display_results(results)
        except:
            pass

    def test_read(self):
        """
        Test steps:

        1. Run a write workload as a preparation
        2. Run a read workload
        """
        base_cmd_w = ("cassandra-stress write no-warmup cl=QUORUM n=30000000 "
                      "-schema 'replication(factor=3)' -port jmx=6868 "
                      "-mode cql3 native -rate threads=100 -errors ignore "
                      "-pop seq=1..30000000")
        base_cmd_r = ("cassandra-stress read no-warmup cl=QUORUM duration=50m "
                      "-schema 'replication(factor=3)' -port jmx=6868 "
                      "-mode cql3 native -rate threads=100 -errors ignore "
                      "-pop 'dist=gauss(1..30000000,15000000,1500000)' ")

        # run a write workload
        stress_queue = self.run_stress_thread(stress_cmd=base_cmd_w, stress_num=2)
        self.get_stress_results(queue=stress_queue, stress_num=2)

        stress_queue = self.run_stress_thread(stress_cmd=base_cmd_r, stress_num=2)
        results = self.get_stress_results(queue=stress_queue, stress_num=2)

        try:
            self.display_results(results)
        except:
            pass

    def test_mixed(self):
        """
        Test steps:

        1. Run a write workload as a preparation
        2. Run a mixed workload
        """
        base_cmd_w = ("cassandra-stress write no-warmup cl=QUORUM n=30000000 "
                      "-schema 'replication(factor=3)' -port jmx=6868 "
                      "-mode cql3 native -rate threads=100 -errors ignore "
                      "-pop seq=1..30000000")
        base_cmd_m = ("cassandra-stress mixed no-warmup cl=QUORUM duration=50m "
                      "-schema 'replication(factor=3)' -port jmx=6868 "
                      "-mode cql3 native -rate threads=100 -errors ignore "
                      "-pop 'dist=gauss(1..30000000,15000000,1500000)' ")

        # run a write workload as a preparation
        stress_queue = self.run_stress_thread(stress_cmd=base_cmd_w, stress_num=2)
        self.get_stress_results(queue=stress_queue, stress_num=2)

        # run a mixed workload
        stress_queue = self.run_stress_thread(stress_cmd=base_cmd_m, stress_num=2)
        results = self.get_stress_results(queue=stress_queue, stress_num=2)

        try:
            self.display_results(results)
        except:
            pass

if __name__ == '__main__':
    main()

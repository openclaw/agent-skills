#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "minitest/autorun"
require "open3"
require "tmpdir"

class InstallSkillsTest < Minitest::Test
  def test_force_skips_target_that_is_source
    Dir.mktmpdir do |dir|
      FileUtils.mkdir_p(File.join(dir, "scripts"))
      FileUtils.mkdir_p(File.join(dir, "skills", "sample"))
      FileUtils.cp(File.join(__dir__, "install-skills"), File.join(dir, "scripts", "install-skills"))
      File.write(File.join(dir, "skills", "sample", "SKILL.md"), "---\nname: sample\ndescription: sample\n---\n")

      stdout, stderr, status = Open3.capture3(
        RbConfig.ruby,
        File.join(dir, "scripts", "install-skills"),
        "--target",
        File.join(dir, "skills"),
        "--force",
        "sample"
      )

      assert status.success?, stderr
      assert_includes stderr, "target is source, skipping"
      assert_empty stdout
      assert_path_exists File.join(dir, "skills", "sample", "SKILL.md")
    end
  end
end

#!/usr/bin/ruby

require 'fileutils'

THUMBWIDTH = 120
THUMBHEIGHT = 90
PREVIEW_DURATION = 5
PREVIEW_FPS = 5
AUDIO_QUALITY = 5
VIDEO_QUALITY = 8
TMP_PATH = '/tmp'

# returns an array [width, height]
def image_size(filename)
  f = IO.popen("file '#{filename}.gif'")
  info = f.readlines[0]
  f.close

  stuff = info.split
  width = stuff[-3].to_i
  height = stuff[-1].to_i

  return [width, height]
end

def generate_preview(input, output, width)
  # mplayer is not very happy with spaces in the output file name, p awesome
  system('mplayer', '-vf', 'scale', '-zoom', '-xy', THUMBWIDTH.to_s, '-benchmark', '-ao', 'null', '-endpos', PREVIEW_DURATION.to_s, '-vo', "gif89a:fps=#{PREVIEW_FPS}:output=#{TMP_PATH}/preview.gif", input) or return false
  system('mogrify', '-layers', 'optimize', "#{TMP_PATH}/preview.gif") or return false
  FileUtils::mv("#{TMP_PATH}/preview.gif", output)
end

if ARGV.empty?
  puts "usage: #{$0} input-video-file <tmp path>"
  exit 1
end

input = ARGV[0]
if ARGV[1]
	TMP_PATH = ARGV[1]
end
output = "#{input}.ogg"
thumbnail = "#{input}.gif"

system('ffmpeg2theora', '--audioquality', AUDIO_QUALITY.to_s, '--videoquality', VIDEO_QUALITY.to_s, '--optimize', '-o', output, input) or exit 1
generate_preview(input, thumbnail, THUMBWIDTH) or return 1

# does this thing fit in the thumbnail box?
width, height = image_size thumbnail
if height > THUMBHEIGHT
  # it doesn't! fit to height instead
  generate_preview(input, thumbnail, THUMBHEIGHT * width / height) or exit 1
end


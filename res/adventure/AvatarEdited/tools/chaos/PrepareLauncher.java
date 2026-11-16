import java.nio.file.*;
import java.util.jar.JarFile;
import jdk.internal.org.objectweb.asm.*;

/** Insert a plane-specific guard before the installed starter selector, in a temporary classpath directory. */
public final class PrepareLauncher implements Opcodes {
    public static void main(String[] args) throws Exception {
        String path = "forge/adventure/util/Config.class";
        String config = "Lforge/adventure/util/Config;";
        String color = "Lforge/card/ColorSet;";
        String difficulty = "Lforge/adventure/data/DifficultyData;";
        String mode = "Lforge/adventure/util/AdventureModes;";
        String deck = "Lforge/deck/Deck;";
        String hooks = "forge/adventure/util/AvatarStarters";
        try (var jar = new JarFile(args[0]); var in = jar.getInputStream(jar.getJarEntry(path))) {
            var reader = new ClassReader(in);
            var writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
            int[] matches = {0};
            reader.accept(new ClassVisitor(ASM8, writer) {
                public MethodVisitor visitMethod(int flags, String name, String desc, String sig, String[] exceptions) {
                    var out = super.visitMethod(flags, name, desc, sig, exceptions);
                    if (!name.equals("starterDeck") || !desc.equals("(" + color + difficulty + mode + "ILforge/card/CardEdition;)" + deck)) return out;
                    matches[0]++;
                    return new MethodVisitor(ASM8, out) {
                        public void visitCode() {
                            super.visitCode();
                            var original = new Label();
                            visitVarInsn(ALOAD, 0);
                            visitVarInsn(ALOAD, 3);
                            visitMethodInsn(INVOKESTATIC, hooks, "handles", "(" + config + mode + ")Z", false);
                            visitJumpInsn(IFEQ, original);
                            for (int i = 0; i < 4; i++) visitVarInsn(ALOAD, i);
                            visitMethodInsn(INVOKESTATIC, hooks, "generate", "(" + config + color + difficulty + mode + ")" + deck, false);
                            visitInsn(ARETURN);
                            visitLabel(original);
                            visitFrame(F_SAME, 0, null, 0, null);
                        }
                    };
                }
            }, 0);
            if (matches[0] != 1) throw new IllegalStateException("Unsupported Forge starter selector");
            Path target = Path.of(args[1], path);
            Files.createDirectories(target.getParent());
            Files.write(target, writer.toByteArray());
        }
    }
}

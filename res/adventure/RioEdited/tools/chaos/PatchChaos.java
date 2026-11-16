import java.nio.file.*;
import java.util.jar.JarFile;
import jdk.internal.org.objectweb.asm.*;

// Build with JDK 21. Inputs: original Adventure JAR and output class directory.
public class PatchChaos {
    public static void main(String[] args) throws Exception {
        String path = "forge/adventure/util/Config.class";
        try (var jar = new JarFile(args[0])) {
            var reader = new ClassReader(jar.getInputStream(jar.getJarEntry(path)));
            var writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
            int[] matches = {0};
            reader.accept(new ClassVisitor(Opcodes.ASM8, writer) {
                public MethodVisitor visitMethod(int flags, String name, String desc,
                                                 String signature, String[] exceptions) {
                    var output = super.visitMethod(flags, name, desc, signature, exceptions);
                    if (!name.equals("starterDeck") || !desc.startsWith(
                            "(Lforge/card/ColorSet;Lforge/adventure/data/DifficultyData;")) return output;
                    return new MethodVisitor(Opcodes.ASM8, output) {
                        public void visitMethodInsn(int op, String owner, String method,
                                                    String type, boolean isInterface) {
                            if (op == Opcodes.INVOKESTATIC && owner.equals("forge/deck/DeckgenUtil")
                                    && method.equals("getRandomOrPreconOrThemeDeck")
                                    && type.equals("(Ljava/lang/String;ZZZ[Ljava/lang/String;)Lforge/deck/Deck;")) {
                                matches[0]++;
                                visitVarInsn(Opcodes.ALOAD, 2);
                                super.visitMethodInsn(op, "forge/adventure/util/RioChaos", "starter",
                                        type.replace(")", "Lforge/adventure/data/DifficultyData;)"), false);
                            } else {
                                super.visitMethodInsn(op, owner, method, type, isInterface);
                            }
                        }
                    };
                }
            }, 0);
            if (matches[0] != 1) throw new IllegalStateException("Unsupported Adventure JAR");
            Path target = Path.of(args[1], path);
            Files.createDirectories(target.getParent());
            Files.write(target, writer.toByteArray());
        }
    }
}
